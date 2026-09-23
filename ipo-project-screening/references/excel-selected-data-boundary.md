# Excel 勾选字段边界

企业数据仅允许来自《数据表信息项-需求-数据探查v2.xlsx》的 `Sheet1` 中“纳入需求（投行）=√”字段。程序只向模型传递其中完成当前任务所需、且已做最小化处理的字段；**未列入下表的企业字段不得出现在输入JSON中**。

## 可输入的数据源

| 输入JSON数组/对象 | Excel表 | 可用字段 |
| --- | --- | --- |
| `basic_registration` | `app_340000_tab00558 企业登记基本信息` | `qymc`、`uniscid`、`cyrs`、`zczb`、`sjzb`、`jyfw`、`industrycogb`、`qyjc` |
| `shareholder_contributions` | `app_340000_tab00568 股东及出资信息表` | `gdlx`、`czbl`、`sje`、`sjfs`、`rjcze`、`sjrq`、`rjczrq`、`rjczfs` |
| `equity_pledges` | `app_340000_tab00575 股权出质登记信息` | `czgqse` |
| `annual_reports` | `app_340000_tab00569 企业年报` | `vendinc`、`progro`、`netinc`、`ratgro`、`liagro` |
| `serious_illegal_records` | `app_340000_tab00566 全省严重违法失信企业名单` | `lrycwfqymdyy`、`sxqx`、`cljg`、`lierrq` |
| `continuing_registration` | `app_rzxd_xcqydjzcxx 存续企业登记注册信息` | `INSURED_PERSON_NUMBER` |
| `tax_payment_records` | `app_rzxd_nsxx 纳税信息` | `PAYABLE_VAT_AMOUNT`、`PAID_VAT_AMOUNT`、`PAYABLE_INCOMETAX_AMOUNT`、`PAID_INCOMETAX_AMOUNT` |
| `dishonest_enforcement_records` | `app_340000_tab00824 失信被执行人信息` | `SXBZXRJTQX` |
| `customs_serious_dishonesty` | `app_340000_tab10176 海关严重失信基础信息` | `MOVE_IN_DATE` |
| `innovation_evaluations` | `app_rzxd_kjyfXX 企业创新评价信息` | `LITTLEGIANT_ENTERPRISES`、`SMALL_ENTERPRISES`、`INNOVATE_ENTERPRISES`、`HIGHANDNEW_ENTERPRISES`、`TECHNOLOGY_ENTERPRISES`、`NATION_HIGHTECH_ENTERPRISE`、`SUPPORT_INFORMATION` |
| `administrative_penalties` | `app_frk_ggxx_xzcf_gb 行政处罚信息` | `XZJG`、`JDRQ`、`ZXQK`、`CFJG`、`CFYJ`、`CFSY`、`CFLB2`、`CFLB1`、`CFMC`、`JDSWH`、`XXFL`、`CF_NR_WFFF`、`CF_NR_FK`、`CF_WFXW` |
| `patents` | `APP_340000_TAB10213 专利信息` | `ZLLX`、`FMMC` |
| `tax_base_indicators` | `TAX_BASE_INFO 税务指标数据` | `tjnf`以及已勾选的 `I1`、`I4`、`I5`、`I6`、`I7`、`I8`、`I9_AY`、`I14`、`I15`季度/同比指标 |
| `bank_cash_flow_income` | `BANK_CASH_FLOW_REVENUE 资金流水明细表（收入表）` | `TRADE_DATE`、`TRADE_TYPE`、`CURRENCY`、`TRADE_AMOUNT`、`TRADE_BALANCE`、`TRADE_EFFECT`、`TRADE_PATH` |
| `bank_cash_flow_expenses` | `BANK_CASH_FLOW_EXPENSES 银行流水汇总（支出表）` | `TRADE_DATE`、`TRADE_TYPE`、`TRADE_COUNT`、`TRADE_BLANCE`、`TRADE_AVG_AMOUNT`、`TRADE_AMOUNT`、`CURRENCY`、`income_expenses` |

水、电、燃气表虽然存在勾选字段，但因含住址、用户号等高敏感字段，当前Agent不接收、不向模型传递；它们不影响本项目的企业池初筛。

## 明确不可输入/不可推断的企业信息

下列信息没有进入本次企业输入边界，即使模型“常识上觉得合理”也必须写为待核实：

- 融资意向、融资金额、投前估值、历史融资、投资人、联系人、决策链、顾问费偏好；
- 审计报告、审计意见、三年一期财务报表、收入确认、客户/供应商、合同、订单、毛利、应收、存货、关联交易；
- IPO申报板块、申报窗口、上市辅导、中介机构、募投项目、股改和完整股权沿革；
- 外部舆情、市场规模、行业估值倍数、客户或投资人名称。

因此，不能用未提供的估值计算 P/S 或 P/E，不能根据流水、税额、专利数或企业登记信息承诺融资/上市，也不能生成带有具体联系人或融资痛点的微信触达话术。

## 输入与配置的区分

企业池JSON只保存上述 Excel 字段。运营方的 `top_k`、重点行业、重点区域、目标市场和我方服务能力属于Agent配置，不是企业事实；它们仅用作批量比较的筛选偏好，不能为任何企业补全事实。
