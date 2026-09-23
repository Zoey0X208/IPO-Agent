"""Prepare neutral evidence packages from selected Excel fields only.

This module deliberately does not rank companies, calculate a score, or assign
business-routing labels. Those judgements belong to the IPO project-screening
Skill executed by the AgentScope model. Local code only normalises selected
Excel records and describes what evidence is available or missing.
"""

from __future__ import annotations

from typing import Any


def build_pre_screen(company: dict[str, Any], selection_context: dict[str, Any]) -> dict[str, Any]:
    """Build a traceable, judgement-free evidence package for the Skill."""
    entity = company["entity"]
    profile = company["table_profile"]
    code_suffix = entity["unified_social_credit_code"][-6:]
    evidence: list[dict[str, Any]] = []
    risk_flags: list[dict[str, Any]] = []
    gaps: list[str] = []

    def add(evidence_id: str, fact: str, source: str) -> str:
        full_id = f"{code_suffix}.{evidence_id}"
        evidence.append({"evidence_id": full_id, "fact": fact, "source": source})
        return full_id

    basic = profile["basic_registration"]
    basic_id = add(
        "basic.registration",
        "已提供企业登记基本信息：行业标识、经营范围、从业人数、注册资本和实缴资本的可用字段已整理。",
        "app_340000_tab00558 企业登记基本信息",
    )
    if basic.get("cyrs") is not None:
        add("basic.employees", f"从业人数：{format_number(basic['cyrs'])}。", "app_340000_tab00558.cyrs")
    if basic.get("zczb") is not None or basic.get("sjzb") is not None:
        add(
            "basic.capital",
            f"注册资本：{format_number(basic.get('zczb'))}；实缴资本：{format_number(basic.get('sjzb'))}。",
            "app_340000_tab00558.zczb/sjzb",
        )

    shareholder_rows = rows(profile, "shareholder_contributions")
    ownership_evidence_ids = [basic_id]
    if shareholder_rows:
        subscribed_total = sum_numbers(shareholder_rows, "sje")
        paid_total = sum_numbers(shareholder_rows, "rjcze")
        ownership_evidence_ids.append(add(
            "ownership.contributions",
            f"已提供股东及出资记录 {len(shareholder_rows)} 条；认缴金额字段合计：{format_number(subscribed_total)}；实缴金额字段合计：{format_number(paid_total)}。",
            "app_340000_tab00568.sje/rjcze/czbl/sjrq/rjczrq",
        ))
    else:
        gaps.append("未提供已勾选的股东及出资记录，无法从当前输入观察出资与股权结构线索。")

    pledge_rows = rows(profile, "equity_pledges")
    if pledge_rows:
        pledge_id = add(
            "ownership.pledges",
            f"已提供股权出质登记记录 {len(pledge_rows)} 条；出质股权数额字段合计：{format_number(sum_numbers(pledge_rows, 'czgqse'))}。",
            "app_340000_tab00575.czgqse",
        )
        risk_flags.append(risk_flag("股权出质", "存在股权出质登记记录，需由Skill结合全量材料判断影响。", [pledge_id]))

    annual_rows = rows(profile, "annual_reports")
    tax_indicator_rows = rows(profile, "tax_base_indicators")
    tax_payment_rows = rows(profile, "tax_payment_records")
    cash_income_rows = rows(profile, "bank_cash_flow_income")
    cash_expense_rows = rows(profile, "bank_cash_flow_expenses")
    financial_ids: list[str] = []
    if annual_rows:
        financial_ids.append(add(
            "finance.annual_reports",
            f"已提供企业年报记录 {len(annual_rows)} 条；包含营业收入、利润总额、净利润、资产与负债增长率等已勾选字段（年报年度字段未纳入本次勾选范围）。",
            "app_340000_tab00569.vendinc/progro/netinc/ratgro/liagro",
        ))
    else:
        gaps.append("未提供已勾选的企业年报财务字段，无法从当前输入观察年度经营财务记录。")
    if tax_indicator_rows:
        periods = [str(row["tjnf"]) for row in tax_indicator_rows if row.get("tjnf") not in (None, "")]
        financial_ids.append(add(
            "finance.tax_indicators",
            f"已提供税务指标记录 {len(tax_indicator_rows)} 条；可识别统计年度：{', '.join(unique_values(periods)) or '未填'}。",
            "TAX_BASE_INFO.tjnf/I1-I15 已勾选指标",
        ))
    if tax_payment_rows:
        financial_ids.append(add(
            "finance.tax_payment",
            f"已提供纳税信息记录 {len(tax_payment_rows)} 条；包含应缴/已缴增值税和企业所得税字段。",
            "app_rzxd_nsxx.PAYABLE_*/PAID_*",
        ))
    if cash_income_rows or cash_expense_rows:
        financial_ids.append(add(
            "finance.cash_flow",
            f"已提供银行流水汇总：收入记录 {len(cash_income_rows)} 条、支出记录 {len(cash_expense_rows)} 条。流水仅用于后续核验线索，不能直接等同营业收入或利润。",
            "BANK_CASH_FLOW_REVENUE/BANK_CASH_FLOW_EXPENSES 已勾选字段",
        ))
    if not financial_ids:
        gaps.append("未提供年报、税务指标、纳税或银行流水中的任何已勾选财务证据。")

    patent_rows = rows(profile, "patents")
    innovation_rows = rows(profile, "innovation_evaluations")
    competitiveness_ids: list[str] = []
    if patent_rows:
        patent_types = unique_values([str(row.get("ZLLX", "")) for row in patent_rows])
        competitiveness_ids.append(add(
            "technology.patents",
            f"已提供专利记录 {len(patent_rows)} 条；专利类型字段：{', '.join(patent_types) or '未填'}。",
            "APP_340000_TAB10213.ZLLX/FMMC",
        ))
    if innovation_rows:
        indicators = selected_innovation_indicators(innovation_rows)
        competitiveness_ids.append(add(
            "technology.innovation",
            f"已提供企业创新评价记录 {len(innovation_rows)} 条；非空创新评价字段：{', '.join(indicators) or '未填'}。",
            "app_rzxd_kjyfXX 已勾选创新评价字段",
        ))
    if not competitiveness_ids:
        gaps.append("未提供专利或创新评价证据，无法从当前输入观察技术与创新线索。")

    compliance_ids: list[str] = []
    for key, evidence_id, label, source in (
        ("serious_illegal_records", "compliance.serious_illegal", "严重违法失信企业名单", "app_340000_tab00566"),
        ("dishonest_enforcement_records", "compliance.dishonest_enforcement", "失信被执行人", "app_340000_tab00824.SXBZXRJTQX"),
        ("customs_serious_dishonesty", "compliance.customs_dishonesty", "海关严重失信", "app_340000_tab10176.MOVE_IN_DATE"),
        ("administrative_penalties", "compliance.administrative_penalties", "行政处罚", "app_frk_ggxx_xzcf_gb 已勾选字段"),
    ):
        count = len(rows(profile, key))
        if count:
            flag_id = add(evidence_id, f"已提供{label}记录 {count} 条。", source)
            compliance_ids.append(flag_id)
            risk_flags.append(risk_flag(label, f"存在{label}记录，需核验事项、履行或整改状态及影响。", [flag_id]))
    if not compliance_ids:
        gaps.append("未提供已勾选的严重违法失信、失信被执行、海关严重失信或行政处罚记录；这不代表不存在相关风险。")

    continuing_rows = rows(profile, "continuing_registration")
    if continuing_rows:
        add(
            "registration.continuing",
            f"已提供存续企业登记注册信息 {len(continuing_rows)} 条，包含参保人数已勾选字段。",
            "app_rzxd_xcqydjzcxx.INSURED_PERSON_NUMBER",
        )

    strategy_alignment = build_strategy_alignment(entity, selection_context, add, basic_id)
    mandatory_limitations = [
        "当前勾选字段不含融资意向、融资金额、估值、融资决策链或联系人；不得据此推断获客转化时点或撰写个性化首次触达话术。",
        "当前勾选字段不含审计报告、审计意见、客户/供应商、合同订单、收入确认、募投项目和IPO申报计划；不得据此确认上市条件、估值或发行时间。",
        "当前证据包仅整理已勾选Excel字段；所有筛选、排序、风险处置和待核验优先级由IPO项目筛选Skill完成。",
    ]
    gaps.extend(mandatory_limitations[:2])

    return {
        "company_name": entity["name"],
        "skill_screening_status": "evidence_prepared_for_skill",
        "local_processing_note": "仅从《数据表信息项-需求-数据探查v2.xlsx》中‘纳入需求（投行）=√’的字段整理证据；本地代码不做分数、项目分流或排序。",
        "entity_resolution": {
            "canonical_name": entity["name"],
            "aliases": entity.get("aliases", []),
            "merge_basis": "仅按已勾选字段 app_340000_tab00558.uniscid 完全一致合并。",
            "manual_confirmation_needed": False,
        },
        "decision_basis": {
            "provided_tables": profile.get("provided_tables", []),
            "financial_evidence_available": bool(financial_ids),
            "ownership_evidence_available": bool(ownership_evidence_ids[1:]),
            "technology_evidence_available": bool(competitiveness_ids),
            "compliance_evidence_available": bool(compliance_ids),
            "strategy_alignment": strategy_alignment,
        },
        "evidence_cards": [
            card("经营与财务证据", financial_ids, "只反映已勾选年报、税务、纳税和流水字段的可得性；不等同审计结论。"),
            card("股权与出资证据", ownership_evidence_ids, "只反映已勾选股东出资、股权出质与基本登记字段；不能确认实控人或历史沿革。"),
            card("技术与创新证据", competitiveness_ids, "只反映专利和创新评价字段；不能据此确认市场地位或客户验证。"),
            card("合规证据", compliance_ids, "存在记录时仅作为核验入口；无记录或未提供记录均不代表无风险。"),
            card("投行服务时点与转化", strategy_alignment["evidence_ids"], "当前勾选字段未覆盖融资与联系人信息，只能标记为待核实。"),
        ],
        "evidence": evidence,
        "risk_flags": risk_flags,
        "data_conflicts": [],
        "data_gaps": unique_values(gaps),
        "next_stage_requirements": mandatory_limitations,
    }


def build_strategy_alignment(entity: dict[str, Any], context: dict[str, Any], add: Any, basic_id: str) -> dict[str, Any]:
    industry_text = f"{entity.get('industry_indicator', '')} {entity.get('business_scope', '')}".lower()
    focus_industries = [str(item).strip() for item in context.get("focus_industries", []) if str(item).strip()]
    matched = [item for item in focus_industries if item.lower() in industry_text]
    if matched:
        evidence_id = add(
            "strategy.industry_context",
            f"企业行业标识/经营范围与运营方关注行业存在文本匹配：{', '.join(matched)}。这仅是配置匹配，不是项目准入结论。",
            "selection_context + app_340000_tab00558.industrycogb/jyfw",
        )
        return {"context_match": matched, "evidence_ids": [basic_id, evidence_id]}
    return {"context_match": [], "evidence_ids": [basic_id]}


def risk_flag(source_category: str, fact: str, evidence_ids: list[str]) -> dict[str, Any]:
    return {
        "source_category": source_category,
        "fact": fact,
        "evidence_ids": evidence_ids,
        "verification": "由IPO项目筛选Skill确定核验优先级和所需材料。",
    }


def card(name: str, evidence_ids: list[str], note: str) -> dict[str, Any]:
    return {"card_name": name, "evidence_ids": evidence_ids, "note": note}


def rows(profile: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = profile.get(key, [])
    return value if isinstance(value, list) else []


def sum_numbers(records: list[dict[str, Any]], field: str) -> float | None:
    values = [to_number(row.get(field)) for row in records]
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def to_number(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def format_number(value: float | None) -> str:
    if value is None:
        return "未填"
    return f"{value:g}"


def unique_values(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def selected_innovation_indicators(records: list[dict[str, Any]]) -> list[str]:
    return unique_values([
        field
        for row in records
        for field, value in row.items()
        if value not in (None, "")
    ])
