"""Tool to load a skill's full content into the dict (auto_skill_mode). Tool execution writes to context; assemble merges dict into context for next LLM input."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.tool.interfaces import ITool
from dare_framework.tool.types import (
    CapabilityKind,
    RunContext,
    ToolResult,
    ToolType,
)

if TYPE_CHECKING:
    from dare_framework.context._internal.context import Context
    from dare_framework.skill.interfaces import ISkillStore


def _error_result(message: str) -> ToolResult:
    return ToolResult(success=False, output={}, error=message, evidence=[])


class SearchSkillTool(ITool, IComponent):
    """Load a skill's full content by skill_id (tool execution). Writes skill full content into context's dict; assemble merges dict into context for next LLM input."""

    def __init__(self, skill_store: "ISkillStore", context: "Context") -> None:
        self._skill_store = skill_store
        self._context = context

    @property
    def name(self) -> str:
        return "search_skill"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TOOL

    @property
    def description(self) -> str:
        return (
            "Load the full instructions for a skill by its skill_id. "
            "Use when you have decided to use a specific skill from the catalog; "
            "the skill's full content will be added to context for the next LLM call."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "Skill identifier from the catalog (e.g. 'code-review', 'pdf-helper').",
                },
            },
            "required": ["skill_id"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string"},
                "skill_name": {"type": "string"},
                "message": {"type": "string"},
            },
        }

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> str:
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
        skill_id = input.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id.strip():
            return _error_result("skill_id is required")

        skill_id = skill_id.strip()
        skill = self._skill_store.get_skill(skill_id)
        if skill is None:
            available = [s.id for s in self._skill_store.list_skills()]
            hint = f" Available: {', '.join(available)}" if available else ""
            return _error_result(f"skill not found: {skill_id}.{hint}")

        self._context.add_loaded_full_skill(skill)
        return ToolResult(
            success=True,
            output={
                "skill_id": skill.id,
                "skill_name": skill.name,
                "message": f"Skill '{skill.name}' loaded. Its full instructions will be in context for the next LLM call. You can use run_skill_script when needed.",
            },
        )


__all__ = ["SearchSkillTool"]
