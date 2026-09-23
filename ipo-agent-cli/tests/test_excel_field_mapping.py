"""Tests for the versioned selected-Excel field mapping."""

from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from ipo_agent.input import BASIC_FIELDS, FIELD_MAPPING, MAPPING_VERSION, TABLE_SPECS


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent
NAMESPACE = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


class ExcelFieldMappingTests(unittest.TestCase):
    def test_mapping_file_is_valid_and_matches_runtime_whitelist(self) -> None:
        mapping_path = ROOT / "config" / "excel-selected-fields.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        self.assertEqual(mapping["schema_version"], MAPPING_VERSION)
        self.assertEqual(tuple(mapping["basic_registration"]["fields"]), BASIC_FIELDS)
        expected_tables = {
            key: (spec["table_name"], tuple(spec["fields"]))
            for key, spec in mapping["tables"].items()
        }
        self.assertEqual(expected_tables, TABLE_SPECS)
        self.assertEqual(mapping, FIELD_MAPPING)

    def test_runtime_fields_are_selected_in_local_workbook_when_available(self) -> None:
        workbook_path = WORKSPACE_ROOT / FIELD_MAPPING["source_workbook"]
        if not workbook_path.is_file():
            self.skipTest("本地未提供原始Excel；CI仅校验版本化映射结构。")

        selected = selected_fields_by_table(workbook_path)
        expected = {"basic_registration": FIELD_MAPPING["basic_registration"], **FIELD_MAPPING["tables"]}
        missing: dict[str, list[str]] = {}
        for input_key, spec in expected.items():
            absent = set(spec["fields"]) - selected.get(spec["table_id"], set())
            if absent:
                missing[input_key] = sorted(absent)
        self.assertEqual(missing, {})


def selected_fields_by_table(workbook_path: Path) -> dict[str, set[str]]:
    with ZipFile(workbook_path) as workbook:
        shared_strings = load_shared_strings(workbook)
        sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
    selected: dict[str, set[str]] = {}
    current_table = ""
    for row in sheet.iter(NAMESPACE + "row"):
        cells = {
            column_name(cell.get("r", "")): cell_value(cell, shared_strings)
            for cell in row.iter(NAMESPACE + "c")
        }
        if cells.get("A"):
            current_table = cells["A"].split("\n", 1)[0].strip()
        if current_table and cells.get("D") == "√" and cells.get("B"):
            selected.setdefault(current_table, set()).add(cells["B"])
    return selected


def load_shared_strings(workbook: ZipFile) -> list[str]:
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in item.iter(NAMESPACE + "t")) for item in root.iter(NAMESPACE + "si")]


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    raw_value = cell.find(NAMESPACE + "v")
    value = "" if raw_value is None else raw_value.text or ""
    if cell.get("t") == "s" and value:
        return shared_strings[int(value)]
    return value


def column_name(reference: str) -> str:
    return "".join(character for character in reference if character.isalpha())


if __name__ == "__main__":
    unittest.main()
