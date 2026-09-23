# 输出模板

## 批量承揽筛选 JSON 契约

只输出一个 JSON 对象，不得使用Markdown代码块或额外解释。所有 `evidence_ids` 必须来自输入。`known_fact` 与 `reasonable_inference` 至少引用一个证据编号；`to_be_verified` 可用空数组。

```json
{
  "data_integrity_summary": {
    "entity_resolution_notes": ["仅基于统一社会信用代码和已勾选简称的归一说明"],
    "material_conflicts": ["当前证据包中的冲突或口径限制"],
    "material_information_gaps": ["影响判断的资料缺口"],
    "treatment_note": "仅使用已勾选Excel字段；未提供不等于无风险。"
  },
  "screening_thesis": "本批企业的相对承揽预研结论，不使用数值评分。",
  "selected_targets": [
    {
      "company_name": "企业名称",
      "selection_order": 1,
      "stage": "engage_now",
      "project_thesis": "优先启动资料沟通和预研的原因，不代表可上市。",
      "possible_capital_market_direction": "仅为待验证研究方向；无证据时写待核实。",
      "selection_reasons": [{"reason": "事实性理由", "evidence_ids": ["证据编号"]}],
      "key_validation_hypothesis": {
        "hypothesis": "最影响继续投入承揽预研资源的待验证假设",
        "why_it_matters": "该假设对当前资料沟通与预研投入的影响",
        "evidence_ids": ["证据编号"],
        "shortest_verification_action": "最短可执行核验动作"
      },
      "six_lens_assessment": [
        {"lens": "industry", "basis": "known_fact", "conclusion": "行业/经营范围与配置的事实或推断", "evidence_ids": ["证据编号"]},
        {"lens": "valuation", "basis": "to_be_verified", "conclusion": "当前勾选字段不含估值与融资信息。", "evidence_ids": []},
        {"lens": "business", "basis": "reasonable_inference", "conclusion": "仅基于专利、创新或经营范围的业务线索", "evidence_ids": ["证据编号"]},
        {"lens": "financial", "basis": "known_fact", "conclusion": "年报/税务/纳税/流水的可得性及核验限制", "evidence_ids": ["证据编号"]},
        {"lens": "legal_compliance", "basis": "to_be_verified", "conclusion": "基于已有合规记录提出的核验事项，或明确无记录不代表无风险", "evidence_ids": []},
        {"lens": "lead_conversion", "basis": "to_be_verified", "conclusion": "当前勾选字段不含融资时点、联系人或决策链。", "evidence_ids": []}
      ],
      "data_conflicts": [],
      "pre_screen_risk_register": [
        {
          "module": "M3",
          "issue": "输入中已出现的财务或口径核验线索",
          "basis": "known_fact",
          "screening_impact": "在项目立项预研前需先完成同期间口径核验。",
          "evidence_ids": ["证据编号"],
          "required_materials": ["审计报告及附注", "纳税申报与收入确认资料"],
          "verification_action": "按同期间对年报、税务和流水进行勾稽并留存差异说明。",
          "urgency": "before_project_review"
        }
      ],
      "information_gaps": ["关键缺口"],
      "mandatory_verifications": [{"item": "需补材料或事项", "urgency": "before_contact", "why": "核验原因"}],
      "first_contact_strategy": "不含个人姓名的通用资料沟通/管理层会面建议。",
      "wechat_first_touch": null,
      "next_action": {"owner_role": "投行承揽人员", "action": "具体资料沟通动作", "target_days": 5}
    }
  ],
  "cultivate_targets": [
    {
      "company_name": "企业名称",
      "stage": "cultivate / pre_project_diagnostic / counselling_cultivate / risk_remediation_first / monitor",
      "current_gap": "当前缺口或风险未闭环",
      "conversion_trigger": "升级为优先接触的条件",
      "next_action": {"owner_role": "投行承揽人员", "action": "具体动作", "target_days": 10}
    }
  ],
  "not_selected": [
    {
      "company_name": "企业名称",
      "reason_not_to_invest_now": "当前暂缓投入资源的原因",
      "re_evaluation_trigger": "重新评估触发条件"
    }
  ],
  "portfolio_observations": ["企业池层面的证据覆盖与风险观察"],
  "context_gaps": ["运营方策略或市场上下文缺口"],
  "compliance_note": "仅用于承揽/立项预研，不构成IPO资格、融资、法律、审计或投资结论。"
}
```

## 填写规则

- `selected_targets` 数量不得超过 `selection_context.top_k`，`selection_order` 从1连续编号；不要求凑满。
- 同一企业只能在 `selected_targets`、`cultivate_targets`、`not_selected` 中出现一次；`cultivate_targets.stage` 只能是 `cultivate`、`pre_project_diagnostic`、`counselling_cultivate`、`risk_remediation_first` 或 `monitor`。
- 每家立即接触企业必须恰有 `industry`、`valuation`、`business`、`financial`、`legal_compliance`、`lead_conversion` 六项视角。
- 每家立即接触企业必须有一个 `key_validation_hypothesis`，且其 `evidence_ids` 非空；假设只说明继续投入承揽预研资源前必须验证的事项，不得将IPO资格或融资意向写成假设。
- `pre_screen_risk_register` 仅登记 M1（主体与出资）、M2（股权出质）、M3（财务口径核验）、M8（法律合规）中输入已出现的线索。每项必须写明筛选影响、材料、动作和核验时点；无已知风险线索时可为空数组。
- 当前输入没有估值、融资金额、融资意向、联系人或决策链时，`valuation`、`lead_conversion` 写 `to_be_verified`，`wechat_first_touch` 必须为 `null`。不可借助外部常识补写个性化话术。
- 有出质、处罚、失信或严重违法记录时，写明记录存在、证据来源、待核验文书/整改材料；不得断言重大性或整改完成。
- 不使用数值评分，不把流水、纳税、专利数量、创新称号或年报单一字段直接等同于上市能力、营业收入、利润、估值或融资成功概率。
