"""skill domain stable interfaces (Kernel boundaries)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.tool.kernel import ITool


class ISkill(IComponent, ABC):
    """Pluggable skill capability for higher-level operations (core)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier."""
        ...

    @property
    def component_type(self) -> Literal[ComponentType.SKILL]:
        """Component category used for config scoping."""
        return ComponentType.SKILL

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...


class ISkillTool(ITool, ABC):
    """Marker interface for tool wrappers that execute skills."""


__all__ = ["ISkill", "ISkillTool"]
