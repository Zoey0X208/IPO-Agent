"""Regression tests for the selected-Excel input boundary."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ipo_agent.input import InputValidationError, load_companies, normalize_company


class InputContractTests(unittest.TestCase):
    def test_minimum_selected_fields_are_accepted(self) -> None:
        company = normalize_company({
            "basic_registration": {"qymc": "测试企业", "uniscid": "91340100TEST000001"},
        }, 1)
        self.assertEqual(company["entity"]["name"], "测试企业")
        self.assertEqual(company["entity"]["unified_social_credit_code"], "91340100TEST000001")

    def test_non_selected_top_level_and_nested_fields_are_rejected(self) -> None:
        base = {"basic_registration": {"qymc": "测试企业", "uniscid": "91340100TEST000001"}}
        for key, value in (("lead_profile", {"x": 1}), ("changes", [])):
            with self.subTest(field=key):
                with self.assertRaises(InputValidationError):
                    normalize_company({**base, key: value}, 1)
        with self.assertRaises(InputValidationError):
            normalize_company({
                "basic_registration": {**base["basic_registration"], "zt": "存续"},
            }, 1)

    def test_same_credit_code_is_merged_and_keeps_selected_alias(self) -> None:
        payload = {
            "companies": [
                {"basic_registration": {"qymc": "测试企业", "qyjc": "测试简称", "uniscid": "91340100TEST000001"}},
                {"basic_registration": {"qymc": "测试企业旧称", "uniscid": "91340100TEST000001"}, "patents": [{"ZLLX": "发明专利", "FMMC": "测试专利"}]},
            ],
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "companies.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            companies = load_companies(path)
        self.assertEqual(len(companies), 1)
        self.assertIn("测试简称", companies[0]["entity"]["aliases"])
        self.assertEqual(len(companies[0]["table_profile"]["patents"]), 1)

    def test_enterprise_json_cannot_contain_operational_context(self) -> None:
        payload = {
            "selection_context": {"top_k": 1},
            "companies": [{"basic_registration": {"qymc": "测试企业", "uniscid": "91340100TEST000001"}}],
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "companies.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(InputValidationError):
                load_companies(path)


if __name__ == "__main__":
    unittest.main()
