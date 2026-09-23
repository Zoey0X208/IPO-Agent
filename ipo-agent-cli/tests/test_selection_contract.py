"""Regression tests for the Skill-owned structured selection contract."""

from __future__ import annotations

import unittest
from pathlib import Path

from ipo_agent.agentscope_agent import validate_batch_selection
from ipo_agent.cli import load_config
from ipo_agent.input import load_companies, load_selection_context
from ipo_agent.schemas import BatchProjectSelection
from ipo_agent.screening import build_pre_screen


ROOT = Path(__file__).resolve().parents[1]


class SelectionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = load_config(ROOT / "config" / "agent.config.json")
        cls.context = load_selection_context(config["selection"])
        companies = load_companies(ROOT / "data" / "example-batch.json")
        cls.packages = [build_pre_screen(company, cls.context) for company in companies]
        cls.evidence_id = cls.packages[0]["evidence"][0]["evidence_id"]

    def valid_payload(self) -> dict:
        lenses = [
            {"lens": lens, "basis": "known_fact", "conclusion": "基于输入证据。", "evidence_ids": [self.evidence_id]}
            for lens in ("industry", "valuation", "business", "financial", "legal_compliance", "lead_conversion")
        ]
        return {
            "data_integrity_summary": {"entity_resolution_notes": [], "material_conflicts": [], "material_information_gaps": [], "treatment_note": "仅使用已勾选Excel字段。"},
            "screening_thesis": "测试批次。",
            "selected_targets": [{
                "company_name": self.packages[0]["company_name"],
                "selection_order": 1,
                "stage": "engage_now",
                "project_thesis": "测试。",
                "possible_capital_market_direction": "待核实。",
                "selection_reasons": [{"reason": "测试理由。", "evidence_ids": [self.evidence_id]}],
                "key_validation_hypothesis": {"hypothesis": "测试假设。", "why_it_matters": "测试影响。", "evidence_ids": [self.evidence_id], "shortest_verification_action": "索取材料。"},
                "six_lens_assessment": lenses,
                "data_conflicts": [],
                "pre_screen_risk_register": [{"module": "M3", "issue": "测试口径线索。", "basis": "known_fact", "screening_impact": "项目立项前核验。", "evidence_ids": [self.evidence_id], "required_materials": ["审计报告"], "verification_action": "勾稽。", "urgency": "before_project_review"}],
                "information_gaps": [],
                "mandatory_verifications": [{"item": "审计报告", "urgency": "before_contact", "why": "测试。"}],
                "first_contact_strategy": "通用资料沟通。",
                "wechat_first_touch": None,
                "next_action": {"owner_role": "投行承揽人员", "action": "索取材料。", "target_days": 5},
            }],
            "cultivate_targets": [{"company_name": self.packages[1]["company_name"], "stage": "monitor", "current_gap": "测试。", "conversion_trigger": "补充材料。", "next_action": {"owner_role": "投行承揽人员", "action": "观察。", "target_days": 10}}],
            "not_selected": [{"company_name": self.packages[2]["company_name"], "reason_not_to_invest_now": "测试。", "re_evaluation_trigger": "补充材料。"}],
            "portfolio_observations": [],
            "context_gaps": [],
            "compliance_note": "测试。",
        }

    def test_hypothesis_and_risk_register_are_traceable(self) -> None:
        selection = BatchProjectSelection.model_validate(self.valid_payload()).model_dump()
        validate_batch_selection(selection, self.packages, self.context)

    def test_unknown_evidence_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["selected_targets"][0]["key_validation_hypothesis"]["evidence_ids"] = ["missing.evidence"]
        selection = BatchProjectSelection.model_validate(payload).model_dump()
        with self.assertRaises(ValueError):
            validate_batch_selection(selection, self.packages, self.context)

    def test_hypothesis_requires_evidence(self) -> None:
        payload = self.valid_payload()
        payload["selected_targets"][0]["key_validation_hypothesis"]["evidence_ids"] = []
        selection = BatchProjectSelection.model_validate(payload).model_dump()
        with self.assertRaises(ValueError):
            validate_batch_selection(selection, self.packages, self.context)


if __name__ == "__main__":
    unittest.main()
