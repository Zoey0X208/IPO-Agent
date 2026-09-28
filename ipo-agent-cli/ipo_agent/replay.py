"""Offline, hash-bound replay for the canonical local evidence preparation case."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .input import FIELD_MAPPING, MAPPING_VERSION, load_companies, load_selection_context
from .report import stable_json_sha256
from .screening import build_pre_screen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "agent.config.json"
DEFAULT_RECEIPT = ROOT / "data" / "canonical-replay" / "example-batch-evidence-v1.json"


def build_evidence_snapshot(source_input: Path, config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Return deterministic fingerprints without invoking the Skill model."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    companies = load_companies(source_input)
    selection_context = load_selection_context(config["selection"])
    evidence_packages = [build_pre_screen(company, selection_context) for company in companies]
    return {
        "field_mapping_schema_version": MAPPING_VERSION,
        "field_mapping_source_workbook_sha256": stable_json_sha256(FIELD_MAPPING["source_workbook"]),
        "companies_received": len(companies),
        "normalized_input_sha256": stable_json_sha256(companies),
        "selection_context_sha256": stable_json_sha256(selection_context),
        "evidence_packages_sha256": stable_json_sha256(evidence_packages),
    }


def verify_canonical_replay(receipt_path: Path = DEFAULT_RECEIPT) -> dict[str, Any]:
    """Compare a versioned local evidence snapshot with the canonical receipt."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    source_input = _resolve_project_relative_path(receipt["source_input"])
    config_path = _resolve_project_relative_path(receipt.get("config_path", "config/agent.config.json"))
    expected = receipt["expected"]
    actual = build_evidence_snapshot(source_input, config_path)
    mismatches = {
        key: {"expected": expected.get(key), "actual": actual.get(key)}
        for key in sorted(set(expected) | set(actual))
        if expected.get(key) != actual.get(key)
    }
    return {
        "case_id": receipt["case_id"],
        "status": "passed" if not mismatches else "failed",
        "source_input": receipt["source_input"],
        "expected": expected,
        "actual": actual,
        "mismatches": mismatches,
    }


def _resolve_project_relative_path(value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("canonical replay 路径必须是项目内的非空相对路径")
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError as error:
        raise ValueError("canonical replay 不允许读取项目目录以外的文件") from error
    if not candidate.is_file():
        raise FileNotFoundError(f"canonical replay 文件不存在：{candidate}")
    return candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="离线复放固定的本地证据整理结果，不调用模型。")
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT, help="canonical replay 收据 JSON")
    parser.add_argument("--print-snapshot", action="store_true", help="输出当前快照，用于人工更新已审核的收据")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.print_snapshot:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        source_input = _resolve_project_relative_path(receipt["source_input"])
        config_path = _resolve_project_relative_path(receipt.get("config_path", "config/agent.config.json"))
        print(json.dumps(build_evidence_snapshot(source_input, config_path), ensure_ascii=False, indent=2))
        return
    result = verify_canonical_replay(args.receipt)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
