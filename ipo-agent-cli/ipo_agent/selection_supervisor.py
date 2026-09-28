"""Deterministic final supervision for Skill-owned batch selection.

This module deliberately does not rank companies, rewrite a model conclusion, or
create a new risk.  It only verifies that the Skill output can be traced back to
the correct company evidence package before it is handed to a human reviewer.
"""

from __future__ import annotations

from typing import Any, Iterable


SIX_LENSES = frozenset({
    "industry",
    "valuation",
    "business",
    "financial",
    "legal_compliance",
    "lead_conversion",
})


def supervise_batch_selection(
    selection: dict[str, Any],
    pre_screens: list[dict[str, Any]],
    selection_context: dict[str, Any],
) -> dict[str, Any]:
    """Validate traceability and return a non-judgemental supervision receipt.

    A ``ValueError`` is intentionally raised for a failed contract.  The caller
    may request one bounded model re-check; this supervisor never repairs or
    changes the selection by itself.
    """
    company_evidence = {
        item["company_name"]: {
            fact["evidence_id"]
            for fact in item.get("evidence", [])
        }
        for item in pre_screens
    }
    company_names = set(company_evidence)
    all_evidence_ids = set().union(*company_evidence.values()) if company_evidence else set()

    selected = selection["selected_targets"]
    _validate_selection_shape(selection, company_names, selection_context)
    for target in selected:
        _validate_selected_target(target, company_evidence, all_evidence_ids)

    return {
        "status": "passed",
        "supervisor": "deterministic-evidence-and-path-supervisor-v1",
        "checks": [
            "every_input_company_has_exactly_one_handling_path",
            "engage_now_order_is_continuous_and_within_top_k",
            "every_engage_now_target_has_each_six_lens_once",
            "all_referenced_evidence_exists_and_belongs_to_the_same_company",
            "known_fact_and_reasonable_inference_are_traceable",
            "wechat_first_touch_is_within_150_characters",
        ],
        "companies_checked": len(company_names),
        "engage_now_checked": len(selected),
    }


def _validate_selection_shape(
    selection: dict[str, Any], company_names: set[str], selection_context: dict[str, Any]
) -> None:
    selected = selection["selected_targets"]
    if len(selected) > int(selection_context["top_k"]):
        raise ValueError("立即接触企业数量超过 selection_context.top_k")

    selected_names = [item["company_name"] for item in selected]
    if len(selected_names) != len(set(selected_names)):
        raise ValueError("立即接触名单中存在重复企业")
    expected_orders = list(range(1, len(selected) + 1))
    if sorted(item["selection_order"] for item in selected) != expected_orders:
        raise ValueError("立即接触名单的 selection_order 必须从 1 连续编号")

    all_names = [*selected_names]
    all_names.extend(item["company_name"] for item in selection["cultivate_targets"])
    all_names.extend(item["company_name"] for item in selection["not_selected"])
    unknown = set(all_names) - company_names
    if unknown:
        raise ValueError(f"输出包含输入中不存在的企业：{', '.join(sorted(unknown))}")
    if len(all_names) != len(set(all_names)):
        raise ValueError("同一企业不能同时出现在多个处理路径")
    missing = company_names - set(all_names)
    if missing:
        raise ValueError(f"输出遗漏输入企业：{', '.join(sorted(missing))}")


def _validate_selected_target(
    target: dict[str, Any],
    company_evidence: dict[str, set[str]],
    all_evidence_ids: set[str],
) -> None:
    company_name = target["company_name"]
    own_evidence_ids = company_evidence[company_name]
    lenses = target["six_lens_assessment"]
    lens_names = [assessment["lens"] for assessment in lenses]
    if len(lens_names) != len(SIX_LENSES) or set(lens_names) != SIX_LENSES:
        raise ValueError(f"{company_name} 的六视角必须各出现一次且不得重复")
    if not target["selection_reasons"]:
        raise ValueError(f"{company_name} 缺少入选理由")

    _require_evidence_for_fact_or_inference(
        company_name, target["selection_reasons"], own_evidence_ids, all_evidence_ids, "selection_reasons"
    )
    hypothesis = target["key_validation_hypothesis"]
    _require_same_company_evidence(
        company_name, hypothesis["evidence_ids"], own_evidence_ids, all_evidence_ids, "key_validation_hypothesis"
    )
    for assessment in lenses:
        if assessment["basis"] != "to_be_verified" and not assessment["evidence_ids"]:
            raise ValueError(f"{company_name} 的 {assessment['lens']} 事实或推断分析缺少证据引用")
        if assessment["evidence_ids"]:
            _require_same_company_evidence(
                company_name,
                assessment["evidence_ids"],
                own_evidence_ids,
                all_evidence_ids,
                f"six_lens_assessment.{assessment['lens']}",
            )
    for conflict in target["data_conflicts"]:
        _require_same_company_evidence(
            company_name, conflict["evidence_ids"], own_evidence_ids, all_evidence_ids, "data_conflicts"
        )
    for risk in target["pre_screen_risk_register"]:
        if risk["basis"] != "to_be_verified" and not risk["evidence_ids"]:
            raise ValueError(f"{company_name} 的 {risk['module']} 风险事项缺少证据引用")
        if risk["evidence_ids"]:
            _require_same_company_evidence(
                company_name,
                risk["evidence_ids"],
                own_evidence_ids,
                all_evidence_ids,
                f"pre_screen_risk_register.{risk['module']}",
            )
    message = target.get("wechat_first_touch")
    if message and len(message) > 150:
        raise ValueError("微信首次触达话术超过 150 字")


def _require_evidence_for_fact_or_inference(
    company_name: str,
    reasons: Iterable[dict[str, Any]],
    own_evidence_ids: set[str],
    all_evidence_ids: set[str],
    location: str,
) -> None:
    for index, reason in enumerate(reasons, start=1):
        _require_same_company_evidence(
            company_name,
            reason["evidence_ids"],
            own_evidence_ids,
            all_evidence_ids,
            f"{location}[{index}]",
        )


def _require_same_company_evidence(
    company_name: str,
    evidence_ids: Iterable[str],
    own_evidence_ids: set[str],
    all_evidence_ids: set[str],
    location: str,
) -> None:
    evidence_ids = list(evidence_ids)
    if not evidence_ids:
        raise ValueError(f"{company_name} 的 {location} 缺少证据引用")
    unknown = set(evidence_ids) - all_evidence_ids
    if unknown:
        raise ValueError(f"{company_name} 的 {location} 引用了不存在的证据编号：{', '.join(sorted(unknown))}")
    cross_company = set(evidence_ids) - own_evidence_ids
    if cross_company:
        raise ValueError(
            f"{company_name} 的 {location} 引用了其他企业的证据编号：{', '.join(sorted(cross_company))}"
        )
