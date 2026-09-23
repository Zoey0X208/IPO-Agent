"""Strict JSON input adapter for the Excel fields selected for investment banking."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class InputValidationError(ValueError):
    """Raised when input is not restricted to the selected Excel fields."""


# Source: 数据表信息项-需求-数据探查v2.xlsx / 表1 需求确认 / 纳入需求（投行）=√
# Personal and account-level fields that were selected in the workbook are
# intentionally omitted from the model payload under data-minimisation rules.
BASIC_FIELDS = (
    "qymc", "uniscid", "cyrs", "zczb", "sjzb", "jyfw", "industrycogb", "qyjc",
)

TABLE_SPECS: dict[str, tuple[str, tuple[str, ...]]] = {
    "shareholder_contributions": (
        "股东及出资信息表",
        ("gdlx", "czbl", "sje", "sjfs", "rjcze", "sjrq", "rjczrq", "rjczfs"),
    ),
    "equity_pledges": ("股权出质登记信息", ("czgqse",)),
    "annual_reports": ("企业年报", ("vendinc", "progro", "netinc", "ratgro", "liagro")),
    "serious_illegal_records": ("全省严重违法失信企业名单", ("lrycwfqymdyy", "sxqx", "cljg", "lierrq")),
    "continuing_registration": ("存续企业登记注册信息", ("INSURED_PERSON_NUMBER",)),
    "tax_payment_records": (
        "纳税信息",
        ("PAYABLE_VAT_AMOUNT", "PAID_VAT_AMOUNT", "PAYABLE_INCOMETAX_AMOUNT", "PAID_INCOMETAX_AMOUNT"),
    ),
    "dishonest_enforcement_records": ("失信被执行人信息", ("SXBZXRJTQX",)),
    "customs_serious_dishonesty": ("海关严重失信基础信息", ("MOVE_IN_DATE",)),
    "innovation_evaluations": (
        "企业创新评价信息",
        (
            "LITTLEGIANT_ENTERPRISES", "SMALL_ENTERPRISES", "INNOVATE_ENTERPRISES",
            "HIGHANDNEW_ENTERPRISES", "TECHNOLOGY_ENTERPRISES", "NATION_HIGHTECH_ENTERPRISE",
            "SUPPORT_INFORMATION",
        ),
    ),
    "administrative_penalties": (
        "行政处罚信息",
        ("XZJG", "JDRQ", "ZXQK", "CFJG", "CFYJ", "CFSY", "CFLB2", "CFLB1", "CFMC", "JDSWH", "XXFL", "CF_NR_WFFF", "CF_NR_FK", "CF_WFXW"),
    ),
    "patents": ("专利信息", ("ZLLX", "FMMC")),
    "tax_base_indicators": (
        "税务指标数据",
        (
            "tjnf", "I1_Q1", "I1_Q2", "I1_Q3", "I1_Q4", "I1_Q1_YOY", "I1_Q2_YOY", "I1_Q3_YOY", "I1_Q4_YOY",
            "I4_Q1", "I4_Q2", "I4_Q3", "I4_Q4", "I4_Q1_YOY", "I4_Q2_YOY", "I4_Q3_YOY", "I4_Q4_YOY",
            "I5_Q1", "I5_Q2", "I5_Q3", "I5_Q4", "I5_Q1_YOY", "I5_Q2_YOY", "I5_Q3_YOY", "I5_Q4_YOY",
            "I6_Q1", "I6_Q2", "I6_Q3", "I6_Q4", "I7_Q1", "I7_Q2", "I7_Q3", "I7_Q4",
            "I8_Q1", "I8_Q2", "I8_Q3", "I8_Q4", "I9_AY", "I14_Q1", "I14_Q2", "I14_Q3", "I14_Q4",
            "I15_HY1", "I15_HY2",
        ),
    ),
    "bank_cash_flow_income": (
        "资金流水明细表（收入表）",
        ("TRADE_DATE", "TRADE_TYPE", "CURRENCY", "TRADE_AMOUNT", "TRADE_BALANCE", "TRADE_EFFECT", "TRADE_PATH"),
    ),
    "bank_cash_flow_expenses": (
        "银行流水汇总（支出表）",
        ("TRADE_DATE", "TRADE_TYPE", "TRADE_COUNT", "TRADE_BLANCE", "TRADE_AVG_AMOUNT", "TRADE_AMOUNT", "CURRENCY", "income_expenses"),
    ),
}


def read_raw_json(input_path: Path) -> Any:
    if input_path.suffix.lower() != ".json":
        raise InputValidationError("仅支持由已勾选 Excel 字段导出的 JSON 输入。")
    try:
        return json.loads(input_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as error:
        raise InputValidationError(f"找不到输入文件：{input_path}") from error
    except json.JSONDecodeError as error:
        raise InputValidationError(f"JSON 格式错误：第 {error.lineno} 行，第 {error.colno} 列。") from error


def load_companies(input_path: Path) -> list[dict[str, Any]]:
    raw = read_raw_json(input_path)
    if isinstance(raw, dict) and isinstance(raw.get("companies"), list):
        reject_unselected_fields(raw, {"companies"}, "JSON 顶层")
        records = raw["companies"]
    elif isinstance(raw, list):
        records = raw
    else:
        raise InputValidationError("顶层必须为 {\"companies\": [...]} 或企业数组。")
    if not records:
        raise InputValidationError("输入中没有企业记录。")
    return merge_same_entity_records([normalize_company(record, index + 1) for index, record in enumerate(records)])


def load_selection_context(selection_config: dict[str, Any]) -> dict[str, Any]:
    """Read operational preferences from config, never from enterprise input JSON."""
    return {
        "target_markets": text_list(selection_config.get("target_markets")),
        "focus_industries": text_list(selection_config.get("focus_industries")),
        "focus_regions": text_list(selection_config.get("focus_regions")),
        "our_strengths": text_list(selection_config.get("our_strengths")),
        "excluded_industries": text_list(selection_config.get("excluded_industries")),
        "horizon_months": bounded_int(selection_config.get("horizon_months"), 36, 6, 120),
        "top_k": bounded_int(selection_config.get("default_top_k"), 10, 1, 30),
    }


def normalize_company(record: Any, index: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise InputValidationError(f"第 {index} 条企业记录不是对象。")
    allowed_keys = {"basic_registration", *TABLE_SPECS}
    reject_unselected_fields(record, allowed_keys, f"第 {index} 条企业记录")

    basic = object_or_empty(record.get("basic_registration"))
    reject_unselected_fields(basic, set(BASIC_FIELDS), f"第 {index} 条企业记录.basic_registration")
    name = text(basic.get("qymc"))
    credit_code = text(basic.get("uniscid"))
    if not name or not credit_code:
        raise InputValidationError(f"第 {index} 条企业记录必须提供已勾选字段 basic_registration.qymc 与 uniscid。")

    normalized_basic = {field: text(basic.get(field)) for field in BASIC_FIELDS}
    for numeric_field in ("cyrs", "zczb", "sjzb"):
        normalized_basic[numeric_field] = non_negative_number(basic.get(numeric_field))

    table_profile: dict[str, Any] = {"basic_registration": normalized_basic, "provided_tables": []}
    provenance = [{"table": "企业登记基本信息", "fields": [field for field in BASIC_FIELDS if normalized_basic.get(field) not in (None, "")] }]
    for key, (table, fields) in TABLE_SPECS.items():
        raw_rows = record.get(key)
        if raw_rows is not None and not isinstance(raw_rows, list):
            raise InputValidationError(f"第 {index} 条企业记录.{key} 必须为数组。")
        rows = minimize_records(raw_rows, fields, f"第 {index} 条企业记录.{key}")
        if raw_rows is not None:
            table_profile["provided_tables"].append(key)
        table_profile[key] = rows
        if rows:
            provenance.append({"table": table, "fields": list(fields)})

    aliases = unique_texts([name, text(basic.get("qyjc"))])
    return {
        "entity": {
            "name": name,
            "aliases": aliases,
            "unified_social_credit_code": credit_code,
            "business_scope": normalized_basic["jyfw"],
            "industry_indicator": normalized_basic["industrycogb"],
        },
        "table_profile": table_profile,
        "provenance": provenance,
    }


def merge_same_entity_records(companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge only records with identical selected Excel field uniscid."""
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for company in companies:
        code = company["entity"]["unified_social_credit_code"]
        if code not in merged:
            merged[code] = company
            order.append(code)
            continue
        merge_company_into(merged[code], company)
    return [merged[key] for key in order]


def merge_company_into(canonical: dict[str, Any], duplicate: dict[str, Any]) -> None:
    canonical["entity"]["aliases"] = unique_texts([
        *canonical["entity"]["aliases"], duplicate["entity"]["name"], *duplicate["entity"]["aliases"],
    ])
    canonical["entity"]["entity_merge_basis"] = "企业登记基本信息.uniscid 一致"
    canonical_profile = canonical["table_profile"]
    duplicate_profile = duplicate["table_profile"]
    canonical_profile["provided_tables"] = unique_texts([
        *canonical_profile["provided_tables"], *duplicate_profile["provided_tables"],
    ])
    for key in TABLE_SPECS:
        canonical_profile[key] = unique_records([*canonical_profile[key], *duplicate_profile[key]])
    canonical["provenance"] = unique_records([*canonical["provenance"], *duplicate["provenance"]])


def minimize_records(value: Any, fields: tuple[str, ...], location: str) -> list[dict[str, Any]]:
    result = []
    for row_index, item in enumerate(list_or_empty(value), start=1):
        if not isinstance(item, dict):
            raise InputValidationError(f"{location}[{row_index}] 必须为对象。")
        reject_unselected_fields(item, set(fields), f"{location}[{row_index}]")
        minimized = {field: item[field] for field in fields if field in item and item[field] not in (None, "")}
        if minimized:
            result.append(minimized)
    return result


def reject_unselected_fields(value: dict[str, Any], allowed: set[str], location: str) -> None:
    unsupported = sorted(key for key, item in value.items() if key not in allowed and item not in (None, "", [], {}))
    if unsupported:
        raise InputValidationError(
            f"{location} 包含未在《数据表信息项-需求-数据探查v2.xlsx》投行勾选范围内的字段：{', '.join(unsupported)}。"
        )


def object_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def text_list(value: Any) -> list[str]:
    return [text(item) for item in value if text(item)] if isinstance(value, list) else []


def unique_texts(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def unique_records(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def non_negative_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def bounded_int(value: Any, default: int, lower: int, upper: int) -> int:
    try:
        return max(lower, min(int(value), upper))
    except (TypeError, ValueError):
        return default
