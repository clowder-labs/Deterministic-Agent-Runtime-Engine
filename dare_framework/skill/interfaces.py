"""Skill domain pluggable interfaces (implementations).

Core skill contracts live in `dare_framework.skill.kernel`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dare_framework.skill.types import Skill


class ISkillLoader(ABC):
    """Loads skills from a source (e.g. filesystem)."""

    @abstractmethod
    def load(self) -> list[Skill]:
        """Load and parse all available skills."""
        ...


class ISkillStore(ABC):
    """Stores and retrieves skills, with optional task-based selection."""

    @abstractmethod
    def list_skills(self) -> list[Skill]:
        """List all loaded skills."""
        ...

    @abstractmethod
    def get_skill(self, skill_id: str) -> Skill | None:
        """Get a skill by id."""
        ...

    @abstractmethod
    def select_for_task(self, query: str, limit: int = 5) -> list[Skill]:
        """Select relevant skills for a natural-language task/query."""
        ...

__all__ = ["ISkillLoader", "ISkillStore"]
