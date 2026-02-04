"""No-op skill implementation."""

from __future__ import annotations

from dare_framework.infra.component import ComponentType
from dare_framework.skill.kernel import ISkill


class NoOpSkill(ISkill):
    """A minimal skill implementation used as a placeholder."""

    @property
    def name(self) -> str:
        return "noop"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SKILL

    @property
    def description(self) -> str:
        return "No-op skill placeholder."

__all__ = ["NoOpSkill"]
