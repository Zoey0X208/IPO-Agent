# 分阶段筛选工作流

## 目的

当输入企业数量较多时，必须先逐家完成独立初筛，再进行组合比较。单企业阶段不能看到其他企业的判断，也不能承担相对排名任务；组合阶段只能比较已经完成的单企业结果和对应证据包。

## 阶段一：single_company_assessment

对每个企业单独执行一次。只读取当前企业的 `evidence_package`、运营方 `selection_context` 和本 Skill 规则。

要求：

1. 不与其他企业比较，不输出名次、分数或组合结论。
2. 只能使用当前企业证据包中的 `evidence_id`；缺失信息必须写入 `information_gaps`，不得补造。
3. `preliminary_path` 只表示初步处理路径：`engage_now`、`cultivate` 或 `not_selected`，不是 IPO、融资或投资结论。
4. `verification_actions` 必须是可执行的下一步核验动作，并说明需要的材料或访谈方向。
5. 输出必须是一个 JSON 对象，不要 Markdown，不要解释文字，结构固定为：

```json
{
  "company_name": "输入企业名称",
  "preliminary_path": "engage_now|cultivate|not_selected",
  "preliminary_reason": "基于当前企业证据的初步理由",
  "evidence_ids": ["当前企业证据包中的 evidence_id"],
  "key_risks": ["已出现或明确待核验的风险"],
  "information_gaps": ["缺少的字段或材料"],
  "verification_actions": ["下一步核验动作"]
}
```

## 阶段二：portfolio_aggregation

在全部单企业评估完成后，才执行一次组合汇总。可读取全部企业的证据包、单企业评估和 `selection_context`。

要求：

1. 由本 Skill 决定企业之间的相对优先级、处理路径和 `selection_order`；不能按固定企业名单或固定分数排序。
2. 综合融资/获客意愿、证据完整性、业务与财务质量、合规风险可核验性、运营方匹配度和下一步转化可执行性；单一收入、利润、专利或风险字段不得直接决定排名。
3. 只有最终 `engage_now` 企业需要完整六视角分析、冲突处理、待验证假设、首触策略和下一步动作；其他企业按最终输出契约给出培育或暂缓理由。
4. 必须覆盖每个输入企业且每家只出现一个最终路径。最终输出严格遵守 `output-templates.md` 中的 `BatchProjectSelection` JSON 契约。
5. 不使用外部检索，不把单企业阶段的初步路径机械照搬为最终路径；如需调整，必须给出基于证据的组合比较理由。

## 分阶段失败处理

单企业 JSON 失败时只允许一次结构修复；修复不能改变事实或路径判断。任一企业仍失败则停止组合汇总并报告失败企业索引。组合 JSON 失败时只允许一次结构修复，之后交人工复核，不得由代码自行补齐排名或业务结论。
