"""Skill store with task-based selection."""

from __future__ import annotations

from dare_framework.skill.interfaces import ISkillLoader, ISkillStore
from dare_framework.skill.types import Skill


class SkillStore(ISkillStore):
    """In-memory skill store with optional selector for task relevance."""

    def __init__(self, skill_loaders: list[ISkillLoader], ) -> None:
        """Initialize store with loader and optional selector.

        Args:
            skill_loaders: Loads skills from source.
            selector: Selects relevant skills for a task. If None, select_for_task
                returns all skills (no filtering).
        """
        self._loader = skill_loaders
        self._load()

    def _load(self) -> None:
        """Load skills from loader and rebuild index."""
        all_skills = []
        all_index = {}
        # todo 需去重处理
        for loader in self._loader:
            skills = loader.load()
            all_skills.extend(skills)
            all_index.update({s.id: s for s in skills})
        self._skills = all_skills
        self._index = all_index

    def reload(self) -> None:
        """Reload skills from source."""
        self._load()

    def list_skills(self) -> list[Skill]:
        """List all loaded skills."""
        return list(self._skills)

    def get_skill(self, skill_id: str) -> Skill | None:
        """Get a skill by id."""
        return self._index.get(skill_id)


__all__ = ["SkillStore"]
