"""Skill-domain deterministic action handlers."""

from __future__ import annotations

from typing import Any

from dare_framework.skill.interfaces import ISkillStore
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.handlers import IActionHandler


class SkillsActionHandler(IActionHandler):
    """Handle deterministic skill-domain actions."""

    def __init__(self, store: ISkillStore) -> None:
        self._store = store

    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.SKILLS_LIST}

    async def invoke(
        self,
        action: ResourceAction,
        _params: dict[str, Any],
    ) -> Any:
        if action != ResourceAction.SKILLS_LIST:
            raise ValueError(f"unsupported skills action: {action.value}")
        skills = []
        for skill in self._store.list_skills():
            skills.append(
                {
                    "id": getattr(skill, "id", None),
                    "name": getattr(skill, "name", None),
                    "description": getattr(skill, "description", None),
                }
            )
        return {"skills": skills}


__all__ = ["SkillsActionHandler"]
