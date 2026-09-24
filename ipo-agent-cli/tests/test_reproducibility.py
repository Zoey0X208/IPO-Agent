"""Tests for non-sensitive reproducibility information in generated reports."""

from __future__ import annotations

import unittest
from pathlib import Path

from ipo_agent.cli import load_config
from ipo_agent.input import MAPPING_VERSION, load_companies, load_selection_context
from ipo_agent.report import build_batch_report
from ipo_agent.screening import build_pre_screen


ROOT = Path(__file__).resolve().parents[1]


class ReproducibilityTests(unittest.TestCase):
    def test_model_report_records_fingerprints_and_effective_execution(self) -> None:
        config = load_config(ROOT / "config" / "agent.config.json")
        companies = load_companies(ROOT / "data" / "example-batch.json")
        context = load_selection_context(config["selection"])
        packages = [build_pre_screen(company, context) for company in companies]
        selection = {
            "content": {},
            "request_id": "request-test",
            "usage": {"total_tokens": 10},
            "execution": {
                "effective_model": "test-model-override",
                "effective_endpoint": "https://example.invalid/v1",
                "temperature": 0.1,
                "max_tokens": 4000,
                "timeout_ms": 60000,
                "repair_attempted": True,
                "attempts": [],
            },
        }

        report = build_batch_report(companies, context, packages, selection, config, "agentscope-openai-compatible-batch-selection")

        reproducibility = report["reproducibility"]
        self.assertEqual(len(reproducibility["normalized_input_sha256"]), 64)
        self.assertEqual(len(reproducibility["agent_config_sha256"]), 64)
        self.assertEqual(reproducibility["excel_selected_field_mapping"]["schema_version"], MAPPING_VERSION)
        self.assertEqual(len(reproducibility["excel_selected_field_mapping"]["sha256"]), 64)
        self.assertTrue(reproducibility["skill"]["files"])
        self.assertEqual(report["meta"]["model"], "test-model-override")
        self.assertTrue(report["meta"]["model_execution"]["repair_attempted"])

    def test_dry_run_does_not_claim_skill_was_loaded(self) -> None:
        config = load_config(ROOT / "config" / "agent.config.json")
        companies = load_companies(ROOT / "data" / "example-batch.json")
        context = load_selection_context(config["selection"])
        packages = [build_pre_screen(company, context) for company in companies]

        report = build_batch_report(companies, context, packages, None, config, "local-evidence-preparation")

        self.assertFalse(report["reproducibility"]["model_execution"]["invoked"])
        self.assertFalse(report["reproducibility"]["skill"]["manifest_available"])


if __name__ == "__main__":
    unittest.main()
