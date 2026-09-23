"""AgentScope 批量项目筛选的结构化输出模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SelectionReason(BaseModel):
    reason: str = Field(description="企业入选或未入选的事实理由。")
    evidence_ids: list[str] = Field(description="支撑理由的输入 evidence_id；没有则为空数组并写待核验。")


class VerificationItem(BaseModel):
    item: str
    urgency: Literal["before_contact", "before_project_review", "monitor"]
    why: str


class NextAction(BaseModel):
    owner_role: str
    action: str
    target_days: int = Field(ge=1, le=90)


class SixLensAssessment(BaseModel):
    lens: Literal["industry", "valuation", "business", "financial", "legal_compliance", "lead_conversion"]
    basis: Literal["known_fact", "reasonable_inference", "to_be_verified"]
    conclusion: str
    evidence_ids: list[str]


class DataConflictHandling(BaseModel):
    field: str
    claims: list[str]
    evidence_ids: list[str]
    handling: str


class KeyValidationHypothesis(BaseModel):
    hypothesis: str = Field(description="最影响是否继续投入承揽预研资源的待验证假设。")
    why_it_matters: str = Field(description="该假设对当前承揽资源投入的影响，不得表述为上市或融资结论。")
    evidence_ids: list[str] = Field(description="支撑该假设的输入证据编号。")
    shortest_verification_action: str = Field(description="最短、可执行的核验动作。")


class PreScreenRiskItem(BaseModel):
    module: Literal["M1", "M2", "M3", "M8"]
    issue: str = Field(description="输入中已出现的风险线索或口径限制。")
    basis: Literal["known_fact", "reasonable_inference", "to_be_verified"]
    screening_impact: str = Field(description="仅描述对承揽预研投入的影响，不得认定上市障碍或风险等级。")
    evidence_ids: list[str]
    required_materials: list[str]
    verification_action: str
    urgency: Literal["before_contact", "before_project_review", "monitor"]


class DataIntegritySummary(BaseModel):
    entity_resolution_notes: list[str]
    material_conflicts: list[str]
    material_information_gaps: list[str]
    treatment_note: str


class SelectedTarget(BaseModel):
    company_name: str
    selection_order: int = Field(ge=1, description="本批次立即接触企业的排序。")
    stage: Literal["engage_now"]
    project_thesis: str = Field(description="本机构值得争取该项目的核心逻辑。")
    possible_capital_market_direction: str = Field(description="仅研究假设，不能表述为上市结论。")
    selection_reasons: list[SelectionReason]
    key_validation_hypothesis: KeyValidationHypothesis
    six_lens_assessment: list[SixLensAssessment] = Field(min_length=6, max_length=6)
    data_conflicts: list[DataConflictHandling]
    pre_screen_risk_register: list[PreScreenRiskItem]
    information_gaps: list[str]
    mandatory_verifications: list[VerificationItem]
    first_contact_strategy: str
    wechat_first_touch: str | None = Field(default=None, max_length=150)
    next_action: NextAction


class CultivateTarget(BaseModel):
    company_name: str
    stage: Literal["cultivate", "pre_project_diagnostic", "counselling_cultivate", "risk_remediation_first", "monitor"]
    current_gap: str
    conversion_trigger: str
    next_action: NextAction


class NotSelectedTarget(BaseModel):
    company_name: str
    reason_not_to_invest_now: str
    re_evaluation_trigger: str


class BatchProjectSelection(BaseModel):
    data_integrity_summary: DataIntegritySummary
    screening_thesis: str = Field(description="本批企业的共同筛选结论。")
    selected_targets: list[SelectedTarget]
    cultivate_targets: list[CultivateTarget]
    not_selected: list[NotSelectedTarget]
    portfolio_observations: list[str]
    context_gaps: list[str]
    compliance_note: str
