"""Search/resolve skill tool with Claude-style prompt and schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dare_framework.tool.kernel import ITool
from dare_framework.tool.types import (
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolResult,
    ToolType,
)

if TYPE_CHECKING:
    from dare_framework.skill.interfaces import ISkillStore
    from dare_framework.skill.types import Skill


_BASE_DESCRIPTION = """Execute a skill within the main conversation.

When users ask you to perform tasks, check if any available skill can help complete
the task more effectively. Skills provide specialized capabilities and domain knowledge.

When users ask you to run a slash command or reference "/<something>"
(for example: "/commit", "/review-pr"), they are referring to a skill.
Use this tool to invoke the corresponding skill.

Important:
- When a skill is relevant, invoke this tool immediately as your first action.
- Never only mention a skill without calling this tool.
- Only use skills listed in "Available skills" below.
"""

_MAX_DESCRIPTION_SKILLS = 50


def _error_result(message: str) -> ToolResult:
    return ToolResult(success=False, output={}, error=message, evidence=[])


def _normalize_skill_name(raw_name: str) -> str:
    """Normalize command-like input to a skill lookup key."""
    return raw_name.strip().lstrip("/")


def _summarize_skill(skill: Skill, max_len: int = 100) -> str:
    """Build a compact one-line summary for tool description."""
    text = (skill.description or "").strip().replace("\n", " ")
    if not text:
        return "no description"
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _build_dynamic_description(skill_store: ISkillStore) -> str:
    """Inject available skill names/basic info into the tool description."""
    skills = sorted(skill_store.list_skills(), key=lambda item: item.id)
    if not skills:
        return _BASE_DESCRIPTION + "\nAvailable skills:\n- (none loaded)"

    lines = ["Available skills:"]
    for skill in skills[:_MAX_DESCRIPTION_SKILLS]:
        lines.append(f"- {skill.id} ({skill.name}): {_summarize_skill(skill)}")
    remaining = len(skills) - _MAX_DESCRIPTION_SKILLS
    if remaining > 0:
        lines.append(
            f"- ... {remaining} additional skills are not loaded into this description."
        )
    return _BASE_DESCRIPTION + "\n" + "\n".join(lines)


def _resolve_skill(skill_store: ISkillStore, skill_name: str) -> Skill | None:
    """Resolve skill by id/name first, then fallback to selection."""
    normalized = _normalize_skill_name(skill_name)
    if not normalized:
        return None

    by_id = skill_store.get_skill(normalized)
    if by_id is not None:
        return by_id

    lowered = normalized.lower()
    for skill in skill_store.list_skills():
        if skill.name.strip().lower() == lowered:
            return skill

    matches = skill_store.select_for_task(normalized, limit=1)
    return matches[0] if matches else None


class SearchSkillTool(ITool):
    """Resolve a skill and return its full prompt payload."""

    def __init__(self, skill_store: ISkillStore) -> None:
        self._skill_store = skill_store
        self._description = _build_dynamic_description(skill_store)

    @property
    def name(self) -> str:
        return "skill"

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "skill": {
                    "type": "string",
                    "description": "The skill name. E.g., 'commit', 'review-pr', or 'pdf'.",
                },
                "args": {
                    "type": "string",
                    "description": "Optional arguments for the skill.",
                },
            },
            "required": ["skill"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "content": {"type": "string"},
                "skill_path": {"type": "string"},
                "scripts": {"type": "object", "additionalProperties": {"type": "string"}},
                "prompt": {"type": "string"},
                "message": {"type": "string"},
                "args": {"type": "string"},
            },
        }

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 5

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.SKILL

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        skill_name = input.get("skill")
        # Backward compatibility with older callers before schema unification.
        if not isinstance(skill_name, str) or not skill_name.strip():
            legacy_id = input.get("skill_id")
            if isinstance(legacy_id, str) and legacy_id.strip():
                skill_name = legacy_id
            else:
                legacy_query = input.get("query")
                if isinstance(legacy_query, str) and legacy_query.strip():
                    skill_name = legacy_query

        if not isinstance(skill_name, str) or not skill_name.strip():
            return _error_result("skill is required")

        skill = _resolve_skill(self._skill_store, skill_name)
        if skill is None:
            available = [f"{s.id} ({s.name})" for s in self._skill_store.list_skills()]
            hint = f" Available: {', '.join(available)}" if available else ""
            return _error_result(f"skill not found: {_normalize_skill_name(skill_name)}.{hint}")

        scripts = {name: str(path) for name, path in skill.scripts.items()}
        args = input.get("args")
        normalized_args = args.strip() if isinstance(args, str) else ""
        return ToolResult(
            success=True,
            output={
                "skill_id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "content": skill.content,
                "skill_path": str(skill.skill_dir) if skill.skill_dir else "",
                "scripts": scripts,
                "prompt": skill.to_context_section(),
                "message": (
                    f"Skill '{skill.name}' loaded. Its full instructions will be in context for "
                    "the next LLM call."
                ),
                "args": normalized_args,
            },
        )


__all__ = ["SearchSkillTool"]
