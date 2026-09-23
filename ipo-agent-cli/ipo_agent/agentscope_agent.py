"""以 AgentScope 2.x 编排 OpenAI 兼容模型。"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from pydantic import SecretStr

from agentscope.credential import OpenAICredential
from agentscope.message import Msg, TextBlock
from agentscope.model import OpenAIChatModel

from .schemas import BatchProjectSelection
from .skill_loader import SkillLoadError, load_skill_instruction


class AgentScopeRequestError(RuntimeError):
    """不会包含 API Key 的可展示错误。"""


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_KEY_FILE = PROJECT_ROOT / "api_key.txt"


def load_api_key() -> str:
    """优先读取环境变量，其次读取被 Git 忽略的本地密钥文件。"""
    for variable_name in ("IPO_AGENT_API_KEY", "CHATANYWHERE_API_KEY"):
        value = os.getenv(variable_name, "").strip()
        if value:
            return value

    if API_KEY_FILE.is_file():
        for line in API_KEY_FILE.read_text(encoding="utf-8-sig").splitlines():
            candidate = line.strip()
            if candidate and not candidate.startswith("#"):
                if candidate.startswith("PASTE_"):
                    return ""
                return candidate
    return ""


def chat_completions_to_base_url(endpoint: str) -> str:
    """把 .../chat/completions 转为 OpenAI AsyncClient 所需 base_url。"""
    parsed = urlparse(endpoint)
    suffix = "/chat/completions"
    path = parsed.path[:-len(suffix)] if parsed.path.endswith(suffix) else parsed.path
    return urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/"), "", "", ""))


def create_model(config: dict[str, Any], model_override: str | None, endpoint_override: str | None) -> OpenAIChatModel:
    api_key = load_api_key()
    if not api_key:
        raise AgentScopeRequestError("未检测到 API Key。请设置 IPO_AGENT_API_KEY / CHATANYWHERE_API_KEY，或在项目根目录 api_key.txt 中粘贴密钥；也可使用 --dry-run 仅运行本地预筛。")
    request = config["request"]
    base_url = chat_completions_to_base_url(endpoint_override or config["endpoint"])
    return OpenAIChatModel(
        credential=OpenAICredential(api_key=SecretStr(api_key), base_url=base_url),
        model=model_override or config["model"],
        parameters=OpenAIChatModel.Parameters(
            temperature=request["temperature"],
            max_tokens=request["max_tokens"],
        ),
        stream=False,
        max_retries=2,
        client_kwargs={"timeout": request["timeout_ms"] / 1000},
    )


async def generate_batch_selection(config: dict[str, Any], companies: list[dict[str, Any]], pre_screens: list[dict[str, Any]], selection_context: dict[str, Any], model_override: str | None = None, endpoint_override: str | None = None) -> dict[str, Any]:
    """让 AgentScope 对整批企业比较后输出项目选择，而不是逐家打分。"""
    try:
        system_instruction = load_skill_instruction(config)
    except SkillLoadError as error:
        raise AgentScopeRequestError(f"无法加载 IPO 筛选 Skill：{error}") from error
    model = create_model(config, model_override, endpoint_override)
    # 仅把本地规则已经生成的、可追溯证据摘要交给模型横向比较。
    # 原始工商、税务和银行记录不发送给模型，既减少上下文噪声，也降低敏感数据暴露面。
    user_payload = json.dumps(
        {"selection_context": selection_context, "evidence_packages": pre_screens},
        ensure_ascii=False,
    )
    message = Msg(
        name="IPOResearchInput",
        role="user",
        content=[TextBlock(text=user_payload)],
    )
    try:
        # 企业池筛选是一次无工具的批量决策。直接用 AgentScope 模型接口避免 ReAct 循环，
        # 同时保留其 OpenAI 兼容模型、消息对象和统一调用能力。
        reply = await model([
            Msg(name="IPOLeadAgent", role="system", content=[TextBlock(text=system_instruction)]),
            message,
        ])
    except Exception as error:  # 框架和上游错误统一转为不泄露密钥的异常
        raise AgentScopeRequestError(f"AgentScope / 模型调用失败：{compact_error(error)}") from error

    try:
        structured = BatchProjectSelection.model_validate(parse_json_text(reply)).model_dump()
        validate_batch_selection(structured, pre_screens, selection_context)
    except Exception as error:
        raise AgentScopeRequestError(f"模型返回内容未通过批量筛选 JSON 契约校验：{compact_error(error)}") from error
    return {
        "content": structured,
        "request_id": reply.id,
        "usage": serialize_usage(reply.usage),
    }


def validate_batch_selection(selection: dict[str, Any], pre_screens: list[dict[str, Any]], selection_context: dict[str, Any]) -> None:
    """Validate structure and traceability without making business routing decisions."""
    company_names = {item["company_name"] for item in pre_screens}
    evidence_ids = {fact["evidence_id"] for item in pre_screens for fact in item.get("evidence", [])}
    selected = selection["selected_targets"]
    if len(selected) > int(selection_context["top_k"]):
        raise ValueError("模型返回的立即接触企业数量超过 selection_context.top_k")
    selected_names = [item["company_name"] for item in selected]
    if len(selected_names) != len(set(selected_names)):
        raise ValueError("模型在立即接触名单中重复了企业")
    expected_orders = list(range(1, len(selected) + 1))
    if sorted(item["selection_order"] for item in selected) != expected_orders:
        raise ValueError("立即接触名单的 selection_order 必须从 1 连续编号")
    for item in selected:
        if not all(assessment["evidence_ids"] for assessment in item["six_lens_assessment"] if assessment["basis"] != "to_be_verified"):
            raise ValueError(f"{item['company_name']} 的事实或推断分析缺少证据引用")
        hypothesis = item["key_validation_hypothesis"]
        if not hypothesis["evidence_ids"]:
            raise ValueError(f"{item['company_name']} 的最大待验证假设缺少证据引用")
        for risk in item["pre_screen_risk_register"]:
            if risk["basis"] != "to_be_verified" and not risk["evidence_ids"]:
                raise ValueError(f"{item['company_name']} 的{risk['module']}风险事项缺少证据引用")
        referenced = {
            evidence_id
            for reason in item["selection_reasons"]
            for evidence_id in reason["evidence_ids"]
        }
        referenced.update(hypothesis["evidence_ids"])
        referenced.update(
            evidence_id
            for assessment in item["six_lens_assessment"]
            for evidence_id in assessment["evidence_ids"]
        )
        referenced.update(
            evidence_id
            for conflict in item["data_conflicts"]
            for evidence_id in conflict["evidence_ids"]
        )
        referenced.update(
            evidence_id
            for risk in item["pre_screen_risk_register"]
            for evidence_id in risk["evidence_ids"]
        )
        invalid = referenced - evidence_ids
        if invalid:
            raise ValueError(f"{item['company_name']} 引用了不存在的证据编号：{', '.join(sorted(invalid))}")
    for item in sorted(selected, key=lambda target: target["selection_order"]):
        message = item.get("wechat_first_touch")
        if message and len(message) > 150:
            raise ValueError("微信首次触达话术超过 150 字")

    all_names: list[str] = [*selected_names]
    all_names.extend(item["company_name"] for item in selection["cultivate_targets"])
    all_names.extend(item["company_name"] for item in selection["not_selected"])
    unknown = set(all_names) - company_names
    if unknown:
        raise ValueError(f"模型返回了输入中不存在的企业：{', '.join(sorted(unknown))}")
    if len(all_names) != len(set(all_names)):
        raise ValueError("同一企业不能同时出现在多个处理路径")


def run_batch_selection(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """供同步 CLI 使用。"""
    return asyncio.run(generate_batch_selection(*args, **kwargs))


def parse_json_text(reply: Any) -> dict[str, Any]:
    text = "".join(block.text for block in reply.content if hasattr(block, "text")).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("模型返回的 JSON 不是对象。")
    return parsed


def serialize_usage(usage: Any) -> dict[str, Any]:
    if not usage:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return dict(usage)
    return {"raw": str(usage)}


def compact_error(error: Exception) -> str:
    text = str(error)
    for key_name in ("IPO_AGENT_API_KEY", "CHATANYWHERE_API_KEY", "ARK_API_KEY"):
        key = os.getenv(key_name, "")
        if key:
            text = text.replace(key, "[REDACTED]")
    return text[:500] or error.__class__.__name__
