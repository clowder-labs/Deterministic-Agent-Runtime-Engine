"""Skill store with task-based selection."""

from __future__ import annotations

from dare_framework.skill.interfaces import ISkillLoader, ISkillSelector
from dare_framework.skill.types import Skill


class SkillStore:
    """In-memory skill store with optional selector for task relevance."""

    def __init__(
        self,
        loader: ISkillLoader,
        selector: ISkillSelector | None = None,
    ) -> None:
        """Initialize store with loader and optional selector.

        Args:
            loader: Loads skills from source.
            selector: Selects relevant skills for a task. If None, select_for_task
                returns all skills (no filtering).
        """
        self._loader = loader
        self._selector = selector
        self._skills: list[Skill] = []
        self._index: dict[str, Skill] = {}
        self._load()

    def _load(self) -> None:
        """Load skills from loader and rebuild index."""
        self._skills = self._loader.load()
        self._index = {s.id: s for s in self._skills}

    def reload(self) -> None:
        """Reload skills from source."""
        self._load()

    def list_skills(self) -> list[Skill]:
        """List all loaded skills."""
        return list(self._skills)

    def get_skill(self, skill_id: str) -> Skill | None:
        """Get a skill by id."""
        return self._index.get(skill_id)

    def select_for_task(self, task_description: str) -> list[Skill]:
        """Select skills relevant to the given task."""
        if not task_description:
            return []
        if self._selector is None:
            return list(self._skills)
        return self._selector.select(task_description, self._skills)


__all__ = ["SkillStore"]
