"""组装批量筛选报告；不输出企业分数。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .input import FIELD_MAPPING, FIELD_MAPPING_PATH, MAPPING_VERSION
from .skill_loader import SkillLoadError, build_skill_manifest


def build_batch_report(companies: list[dict[str, Any]], selection_context: dict[str, Any], pre_screens: list[dict[str, Any]], selection: dict[str, Any] | None, config: dict[str, Any], mode: str) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for item in pre_screens:
        status = item["skill_screening_status"]
        counts[status] = counts.get(status, 0) + 1
    report: dict[str, Any] = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "framework": "agentscope-skill" if selection else "local-evidence-preparation",
            "selection_version": config["version"],
            "model": selection.get("execution", {}).get("effective_model") if selection else None,
            "notice": "本报告用于批量获客研究和人工项目筛选，不构成发行上市资格、时间表或融资结果判断。",
        },
        "reproducibility": build_reproducibility_manifest(companies, config, selection),
        "selection_context": selection_context,
        "run_summary": {
            "companies_received": len(companies),
            "evidence_preparation_distribution": counts,
            "final_selection_available": bool(selection),
        },
        "data_integrity_summary": build_data_integrity_summary(companies, pre_screens),
        "pre_screening": pre_screens,
        "batch_project_selection": selection["content"] if selection else None,
        "provenance_by_company": [{"company_name": company["entity"]["name"], "provenance": company["provenance"]} for company in companies],
    }
    if selection:
        report["meta"]["model_request_id"] = selection.get("request_id", "")
        report["meta"]["usage"] = selection.get("usage", {})
        report["meta"]["model_execution"] = selection.get("execution", {})
    return report


def build_reproducibility_manifest(companies: list[dict[str, Any]], config: dict[str, Any], selection: dict[str, Any] | None) -> dict[str, Any]:
    """Record non-sensitive fingerprints for a reproducible screening run."""
    manifest: dict[str, Any] = {
        "normalized_input_sha256": stable_json_sha256(companies),
        "agent_config_sha256": stable_json_sha256(config),
        "excel_selected_field_mapping": {
            "schema_version": MAPPING_VERSION,
            "source_workbook": FIELD_MAPPING["source_workbook"],
            "sha256": sha256_file(FIELD_MAPPING_PATH),
        },
        "model_execution": selection.get("execution", {}) if selection else {"invoked": False},
    }
    if selection:
        loaded_skill_manifest = selection.get("skill_manifest")
        if isinstance(loaded_skill_manifest, dict):
            manifest["skill"] = loaded_skill_manifest
        else:
            try:
                manifest["skill"] = build_skill_manifest(config)
            except SkillLoadError as error:
                manifest["skill"] = {"manifest_available": False, "reason": str(error)}
    else:
        manifest["skill"] = {"manifest_available": False, "reason": "dry_run 未加载 Skill"}
    return manifest


def stable_json_sha256(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256_file(path: Any) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_data_integrity_summary(companies: list[dict[str, Any]], pre_screens: list[dict[str, Any]]) -> dict[str, Any]:
    """Expose selected-Excel entity normalisation and evidence limitations."""
    entity_resolution = []
    conflicts = []
    material_gaps = []
    for company, pre_screen in zip(companies, pre_screens, strict=True):
        resolution = pre_screen.get("entity_resolution", {})
        entity_resolution.append({
            "company_name": company["entity"]["name"],
            "aliases": resolution.get("aliases", []),
            "merge_basis": resolution.get("merge_basis", "未提供"),
            "manual_confirmation_needed": resolution.get("manual_confirmation_needed", False),
        })
        for conflict in pre_screen.get("data_conflicts", []):
            conflicts.append({"company_name": company["entity"]["name"], **conflict})
        material_gaps.extend(
            f"{company['entity']['name']}：{gap}"
            for gap in pre_screen.get("data_gaps", [])
            if "当前勾选字段不含" in gap or "未提供" in gap
        )
    return {
        "entities_after_normalization": len(companies),
        "entity_resolution": entity_resolution,
        "material_conflicts": conflicts,
        "material_information_gaps": material_gaps,
        "treatment_note": "企业数据仅来自《数据表信息项-需求-数据探查v2.xlsx》中标记为“纳入需求（投行）=√”的字段；未勾选字段一律不输入、不推断。",
    }
