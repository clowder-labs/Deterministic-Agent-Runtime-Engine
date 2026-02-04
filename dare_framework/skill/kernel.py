"""skill domain stable interfaces (Kernel boundaries)."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.tool.kernel import ITool


@runtime_checkable
class ISkill(IComponent, Protocol):
    """Pluggable skill capability for higher-level operations (core)."""

    @property
    def name(self) -> str:
        """Unique skill identifier."""
        ...

    @property
    def component_type(self) -> Literal[ComponentType.SKILL]:
        """Component category used for config scoping."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

@runtime_checkable
class ISkillTool(ITool, Protocol):
    """Marker interface for tool wrappers that execute skills."""


__all__ = ["ISkill", "ISkillTool"]
