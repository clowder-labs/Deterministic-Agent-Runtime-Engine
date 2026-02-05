"""Tool for selecting a skill and returning its prompt content."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.skill.kernel import ISkillTool
from dare_framework.skill.types import Skill
from dare_framework.tool.types import CapabilityKind, RunContext, ToolResult, ToolType

if TYPE_CHECKING:
    from dare_framework.skill.interfaces import ISkillStore


class SearchSkillTool(ISkillTool):
    """Select a skill by query or id and return its prompt content."""

    def __init__(self, skill_store: ISkillStore) -> None:
        self._skill_store = skill_store

    @property
    def name(self) -> str:
        return "skill"

    @property
    def description(self) -> str:
        return (
            "Search for a relevant skill and return its prompt content. "
            "Use when you need specialized instructions from a skill."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query describing the needed skill.",
                },
                "skill_id": {
                    "type": "string",
                    "description": "Optional explicit skill id to fetch directly.",
                },
            },
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
            },
            "required": ["skill_id", "name", "description", "content", "prompt"],
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
        skill = _resolve_skill(self._skill_store, input)
        if skill is None:
            return ToolResult(success=False, output={}, error="skill not found", evidence=[])
        return ToolResult(
            success=True,
            output={
                "skill_id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "content": skill.content,
                "skill_path": str(skill.skill_dir) if skill.skill_dir else "",
                "scripts": {name: str(path) for name, path in skill.scripts.items()},
                "prompt": skill.to_context_section(),
            },
            error=None,
            evidence=[],
        )


def _resolve_skill(skill_store: ISkillStore, input_data: dict[str, Any]) -> Skill | None:
    skill_id = input_data.get("skill_id")
    if isinstance(skill_id, str) and skill_id.strip():
        return skill_store.get_skill(skill_id.strip())
    query = input_data.get("query")
    if not isinstance(query, str) or not query.strip():
        return None
    matches = skill_store.select_for_task(query.strip())
    return matches[0] if matches else None


__all__ = ["SearchSkillTool"]
