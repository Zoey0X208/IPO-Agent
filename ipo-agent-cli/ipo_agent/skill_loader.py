"""在运行时加载本地 Skill，避免把业务提示词写死在 Agent 配置或代码中。"""

from __future__ import annotations

from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SkillLoadError(RuntimeError):
    """Skill 路径、入口或引用资料不符合运行要求。"""


def load_skill_instruction(config: dict[str, Any]) -> str:
    """读取 Skill 入口及本次运行模式所需的引用资料。"""
    spec = config.get("skill")
    if not isinstance(spec, dict):
        raise SkillLoadError("配置缺少 skill 对象。")
    configured_path = spec.get("path")
    if not isinstance(configured_path, str) or not configured_path.strip():
        raise SkillLoadError("skill.path 必须是非空路径。")

    skill_root = Path(configured_path)
    if not skill_root.is_absolute():
        skill_root = PROJECT_ROOT / skill_root
    skill_root = skill_root.resolve()
    entry = skill_root / "SKILL.md"
    if not entry.is_file():
        raise SkillLoadError(f"找不到 Skill 入口文件：{entry}")

    parts = [read_skill_file(entry, skill_root)]
    references = spec.get("references", [])
    if not isinstance(references, list) or not all(isinstance(item, str) for item in references):
        raise SkillLoadError("skill.references 必须是字符串数组。")
    for relative_path in references:
        reference = (skill_root / relative_path).resolve()
        if not is_within(reference, skill_root):
            raise SkillLoadError(f"Skill 引用越出 Skill 目录：{relative_path}")
        if not reference.is_file():
            raise SkillLoadError(f"找不到 Skill 引用资料：{relative_path}")
        parts.append(read_skill_file(reference, skill_root))
    return "\n\n".join(parts)


def read_skill_file(path: Path, skill_root: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8-sig").strip()
    except UnicodeDecodeError as error:
        raise SkillLoadError(f"Skill 文件必须使用 UTF-8 编码：{path}") from error
    if not content:
        raise SkillLoadError(f"Skill 文件为空：{path}")
    relative_path = path.relative_to(skill_root).as_posix()
    return f"<!-- 已加载 Skill 文件：{relative_path} -->\n{content}"


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False
