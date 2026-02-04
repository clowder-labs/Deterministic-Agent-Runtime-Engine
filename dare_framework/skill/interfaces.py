"""Skill domain pluggable interfaces (implementations).

Core skill contracts live in `dare_framework.skill.kernel`.
"""

from __future__ import annotations

from typing import Protocol

from dare_framework.skill.types import Skill


class ISkillLoader(Protocol):
    """Loads skills from a source (e.g. filesystem)."""

    def load(self) -> list[Skill]:
        """Load and parse all available skills."""
        ...


class ISkillStore(Protocol):
    """Stores and retrieves skills, with optional task-based selection."""

    def list_skills(self) -> list[Skill]:
        """List all loaded skills."""
        ...

    def get_skill(self, skill_id: str) -> Skill | None:
        """Get a skill by id."""
        ...

    def select_for_task(self, task_description: str) -> list[Skill]:
        """Select skills relevant to the given task description."""
        ...


class ISkillSelector(Protocol):
    """Selects relevant skills for a task."""

    def select(self, task_description: str, skills: list[Skill]) -> list[Skill]:
        """Select skills relevant to the task from the given list."""
        ...


__all__ = ["ISkillLoader", "ISkillStore", "ISkillSelector"]
