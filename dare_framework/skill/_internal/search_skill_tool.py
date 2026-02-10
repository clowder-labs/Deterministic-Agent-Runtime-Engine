"""Search/resolve skill tool with Claude-style prompt and schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from dare_framework.tool.kernel import ITool
from dare_framework.tool._internal.util.__tool_schema_util import (
    infer_input_schema_from_execute,
    infer_output_schema_from_execute,
)
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
        schema = infer_input_schema_from_execute(type(self).execute)
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        return schema

    @property
    def output_schema(self) -> dict[str, Any]:
        return infer_output_schema_from_execute(type(self).execute) or {}

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

    # noinspection PyMethodOverriding
    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        skill: str,
        args: str = "",
    ) -> ToolResult[SearchSkillOutput]:
        """Resolve a skill and return prompt payload.

        Args:
            run_context: Runtime invocation context.
            skill: Skill id or name to resolve.
            args: Optional skill arguments.

        Returns:
            Resolved skill metadata and prompt payload.
        """
        _ = run_context
        if not isinstance(skill, str) or not skill.strip():
            return _error_result("skill is required")

        resolved = _resolve_skill(self._skill_store, skill)
        if resolved is None:
            available = [f"{s.id} ({s.name})" for s in self._skill_store.list_skills()]
            hint = f" Available: {', '.join(available)}" if available else ""
            return _error_result(f"skill not found: {_normalize_skill_name(skill)}.{hint}")

        scripts = {name: str(path) for name, path in resolved.scripts.items()}
        normalized_args = args.strip() if isinstance(args, str) else ""
        return ToolResult(
            success=True,
            output={
                "skill_id": resolved.id,
                "name": resolved.name,
                "description": resolved.description,
                "content": resolved.content,
                "skill_path": str(resolved.skill_dir) if resolved.skill_dir else "",
                "scripts": scripts,
                "prompt": resolved.to_context_section(),
                "message": (
                    f"Skill '{resolved.name}' loaded. Its full instructions will be in context for "
                    "the next LLM call."
                ),
                "args": normalized_args,
            },
        )


class SearchSkillOutput(TypedDict):
    skill_id: str
    name: str
    description: str
    content: str
    skill_path: str
    scripts: dict[str, str]
    prompt: str
    message: str
    args: str


__all__ = ["SearchSkillTool"]
