"""Generate a reproducible 18-company synthetic batch using only selected Excel fields."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "demo-batch-18.json"


def company(index: int, industry: str) -> dict:
    return {
        "basic_registration": {
            "qymc": f"测试企业{index:02d}号{industry}",
            "uniscid": f"91340100DEMO{index:010d}",
            "qyjc": f"测试{index:02d}",
            "cyrs": 110 + index * 17,
            "zczb": 3000 + index * 200,
            "sjzb": 2500 + index * 160,
            "jyfw": f"{industry}研发、生产和销售",
            "industrycogb": "制造业",
        },
        "shareholder_contributions": [
            {"gdlx": "企业法人", "czbl": 62, "sje": 2400, "sjfs": "货币", "rjcze": 2400, "sjrq": "2025-06-30", "rjczrq": "2025-06-30", "rjczfs": "货币"},
            {"gdlx": "合伙企业", "czbl": 18, "sje": 700, "sjfs": "货币", "rjcze": 700, "sjrq": "2025-08-15", "rjczrq": "2025-08-15", "rjczfs": "货币"},
        ],
    }


def add_financial_evidence(record: dict, multiplier: int = 1) -> None:
    record["annual_reports"] = [
        {"vendinc": 28000 * multiplier, "progro": 3600 * multiplier, "netinc": 2900 * multiplier, "ratgro": 12, "liagro": 8},
        {"vendinc": 35500 * multiplier, "progro": 4700 * multiplier, "netinc": 3900 * multiplier, "ratgro": 15, "liagro": 9},
    ]
    record["tax_base_indicators"] = [
        {"tjnf": "2025", "I1_Q1": 9800 * multiplier, "I1_Q1_YOY": 12, "I4_Q1": 9800 * multiplier, "I5_Q1": 1100 * multiplier, "I14_Q1": 260 * multiplier},
        {"tjnf": "2026", "I1_Q1": 11200 * multiplier, "I1_Q1_YOY": 14, "I4_Q1": 11200 * multiplier, "I5_Q1": 1300 * multiplier, "I14_Q1": 300 * multiplier},
    ]
    record["tax_payment_records"] = [{
        "PAYABLE_VAT_AMOUNT": 420 * multiplier,
        "PAID_VAT_AMOUNT": 420 * multiplier,
        "PAYABLE_INCOMETAX_AMOUNT": 210 * multiplier,
        "PAID_INCOMETAX_AMOUNT": 210 * multiplier,
    }]
    record["bank_cash_flow_income"] = [{"TRADE_DATE": "202607", "TRADE_TYPE": "转账", "CURRENCY": "CNY", "TRADE_AMOUNT": 4500 * multiplier, "TRADE_BALANCE": 900, "TRADE_EFFECT": "收入", "TRADE_PATH": "银行"}]
    record["bank_cash_flow_expenses"] = [{"TRADE_DATE": "202607", "TRADE_TYPE": "转账", "TRADE_COUNT": 18, "TRADE_BLANCE": 700, "TRADE_AVG_AMOUNT": 180, "TRADE_AMOUNT": 3200 * multiplier, "CURRENCY": "CNY", "income_expenses": "支出"}]


def make_demo() -> dict:
    industries = ["集成电路", "智能装备", "先进材料", "工业机器人", "功率半导体"]
    records: list[dict] = []

    for index in range(1, 6):
        item = company(index, industries[(index - 1) % len(industries)])
        add_financial_evidence(item, index)
        item["innovation_evaluations"] = [{"HIGHANDNEW_ENTERPRISES": "是", "SMALL_ENTERPRISES": "是"}]
        item["patents"] = [{"ZLLX": "发明专利", "FMMC": "测试核心工艺"}]
        records.append(item)

    for index in range(6, 11):
        item = company(index, industries[(index - 1) % len(industries)])
        if index <= 8:
            add_financial_evidence(item)
        item["innovation_evaluations"] = [{"HIGHANDNEW_ENTERPRISES": "是"}]
        item["patents"] = [{"ZLLX": "发明专利", "FMMC": "测试技术方案"}]
        records.append(item)

    risk_rows = [
        ("equity_pledges", [{"czgqse": 1600}]),
        ("administrative_penalties", [{"XZJG": "测试机关", "JDRQ": "2026-03-12", "ZXQK": "待核验", "CFMC": "测试处罚"}]),
        ("dishonest_enforcement_records", [{"SXBZXRJTQX": "待核验"}]),
        ("serious_illegal_records", [{"lrycwfqymdyy": "待核验原因", "sxqx": "待核验", "cljg": "待核验", "lierrq": "2026-03-12"}]),
    ]
    for index, (key, value) in enumerate(risk_rows, start=11):
        item = company(index, industries[(index - 1) % len(industries)])
        add_financial_evidence(item)
        item[key] = value
        records.append(item)

    for index in range(15, 19):
        item = company(index, "精密制造")
        item["shareholder_contributions"] = []
        item["basic_registration"]["cyrs"] = None
        records.append(item)

    return {"companies": records}


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(make_demo(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成仅含已勾选Excel字段的18家虚构测试企业：{OUTPUT}")
