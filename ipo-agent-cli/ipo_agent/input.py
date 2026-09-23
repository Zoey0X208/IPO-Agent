"""Strict JSON input adapter for the Excel fields selected for investment banking."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class InputValidationError(ValueError):
    """Raised when input is not restricted to the selected Excel fields."""


# Source: 数据表信息项-需求-数据探查v2.xlsx / 表1 需求确认 / 纳入需求（投行）=√.
# The versioned mapping is deliberately separate from business screening logic.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIELD_MAPPING_PATH = PROJECT_ROOT / "config" / "excel-selected-fields.json"


def load_field_mapping() -> dict[str, Any]:
    try:
        mapping = json.loads(FIELD_MAPPING_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"找不到Excel字段映射文件：{FIELD_MAPPING_PATH}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Excel字段映射文件格式错误：{FIELD_MAPPING_PATH}") from error
    if not isinstance(mapping, dict) or not isinstance(mapping.get("schema_version"), str):
        raise RuntimeError("Excel字段映射必须包含 schema_version。")
    if not isinstance(mapping.get("basic_registration"), dict) or not isinstance(mapping.get("tables"), dict):
        raise RuntimeError("Excel字段映射缺少 basic_registration 或 tables。")
    return mapping


def fields_from_spec(spec: dict[str, Any], location: str) -> tuple[str, ...]:
    table_id = spec.get("table_id")
    table_name = spec.get("table_name")
    fields = spec.get("fields")
    if not isinstance(table_id, str) or not table_id or not isinstance(table_name, str) or not table_name:
        raise RuntimeError(f"Excel字段映射 {location} 缺少 table_id 或 table_name。")
    if not isinstance(fields, list) or not fields or not all(isinstance(field, str) and field for field in fields):
        raise RuntimeError(f"Excel字段映射 {location}.fields 必须是非空字符串数组。")
    if len(fields) != len(set(fields)):
        raise RuntimeError(f"Excel字段映射 {location}.fields 存在重复字段。")
    return tuple(fields)


FIELD_MAPPING = load_field_mapping()
MAPPING_VERSION = FIELD_MAPPING["schema_version"]
BASIC_SOURCE = FIELD_MAPPING["basic_registration"]
BASIC_FIELDS = fields_from_spec(BASIC_SOURCE, "basic_registration")
if not {"qymc", "uniscid"}.issubset(BASIC_FIELDS):
    raise RuntimeError("Excel字段映射 basic_registration 必须包含 qymc 和 uniscid。")

TABLE_SOURCES: dict[str, dict[str, Any]] = FIELD_MAPPING["tables"]
TABLE_SPECS: dict[str, tuple[str, tuple[str, ...]]] = {
    key: (spec["table_name"], fields_from_spec(spec, f"tables.{key}"))
    for key, spec in TABLE_SOURCES.items()
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
    provenance = [{
        "mapping_version": MAPPING_VERSION,
        "table_id": BASIC_SOURCE["table_id"],
        "table": BASIC_SOURCE["table_name"],
        "fields": [field for field in BASIC_FIELDS if normalized_basic.get(field) not in (None, "")],
    }]
    for key, (table, fields) in TABLE_SPECS.items():
        raw_rows = record.get(key)
        if raw_rows is not None and not isinstance(raw_rows, list):
            raise InputValidationError(f"第 {index} 条企业记录.{key} 必须为数组。")
        rows = minimize_records(raw_rows, fields, f"第 {index} 条企业记录.{key}")
        if raw_rows is not None:
            table_profile["provided_tables"].append(key)
        table_profile[key] = rows
        if rows:
            provenance.append({
                "mapping_version": MAPPING_VERSION,
                "table_id": TABLE_SOURCES[key]["table_id"],
                "table": table,
                "fields": list(fields),
            })

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
    # Strictly reject every unknown key, including empty placeholders.  Otherwise a
    # caller could silently send non-selected Excel fields that happen to be blank
    # in the current batch, weakening the input contract.
    unsupported = sorted(key for key in value if key not in allowed)
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
