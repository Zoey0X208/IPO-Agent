"""批量 IPO 项目筛选命令行编排。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .agentscope_agent import AgentScopeRequestError, run_batch_selection
from .input import InputValidationError, load_companies, load_selection_context
from .report import build_batch_report
from .screening import build_pre_screen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "agent.config.json"
DEFAULT_OUTPUT = ROOT / "output" / "ipo-project-selection.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ipo-agent",
        description="批量筛选可承揽 IPO 项目候选的 AgentScope Agent（仅 JSON 输入）。",
    )
    parser.add_argument("--input", required=True, type=Path, help="企业池 JSON；顶层仅允许 {\"companies\": [...]}，企业字段必须来自已勾选Excel范围。")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"输出报告路径（默认：{DEFAULT_OUTPUT}）。")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Agent 配置 JSON 路径。")
    parser.add_argument("--dry-run", action="store_true", help="不调用外部模型，仅输出证据整理结果，不做业务分流或项目排序。")
    parser.add_argument("--model", help="临时覆盖配置中的模型名。")
    parser.add_argument("--endpoint", help="临时覆盖配置中的 Chat Completions 地址。")
    return parser


def load_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise InputValidationError(f"找不到配置文件：{path}") from error
    except json.JSONDecodeError as error:
        raise InputValidationError(f"配置 JSON 格式错误：第 {error.lineno} 行。") from error
    required = {"version", "endpoint", "model", "request", "selection", "skill"}
    absent = required - config.keys()
    if absent:
        raise InputValidationError("配置缺少字段：" + "、".join(sorted(absent)))
    return config


def main() -> None:
    args = build_parser().parse_args()
    try:
        config = load_config(args.config)
        companies = load_companies(args.input)
        context = load_selection_context(config["selection"])
        print(f"正在整理 {len(companies)} 家企业的筛选证据…")
        pre_screens = [build_pre_screen(company, context) for company in companies]
        selection = None
        mode = "local-evidence-preparation"
        if not args.dry_run:
            print("正在通过 AgentScope 比较企业池并选择项目候选…")
            selection = run_batch_selection(config, companies, pre_screens, context, args.model, args.endpoint)
            mode = "agentscope-openai-compatible-batch-selection"
        report = build_batch_report(companies, context, pre_screens, selection, config, mode)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"完成。报告已写入：{args.output.resolve()}")
    except (InputValidationError, AgentScopeRequestError) as error:
        print(f"错误：{error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
