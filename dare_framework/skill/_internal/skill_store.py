"""Skill store with task-based selection."""

from __future__ import annotations

from dare_framework.skill.interfaces import ISkillLoader, ISkillStore
from dare_framework.skill.types import Skill


class SkillStore(ISkillStore):
    """In-memory skill store with optional selector for task relevance."""

    def __init__(
        self,
        skill_loaders: list[ISkillLoader],
        disabled_skill_ids: set[str] | None = None,
    ) -> None:
        """Initialize store with one or more loaders and optional disabled ids.

        Args:
            skill_loaders: Loads skills from source.
            disabled_skill_ids: Skill ids to exclude from the final store.
        """
        self._loader = skill_loaders
        self._disabled_skill_ids = {item.strip() for item in (disabled_skill_ids or set()) if item.strip()}
        self._load()

    def _load(self) -> None:
        """Load skills from loader and rebuild index."""
        all_skills = []
        all_index = {}
        for loader in self._loader:
            skills = loader.load()
            for skill in skills:
                if skill.id in self._disabled_skill_ids:
                    continue
                if skill.id in all_index:
                    continue
                all_skills.append(skill)
                all_index[skill.id] = skill
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

    def select_for_task(self, query: str, limit: int = 5) -> list[Skill]:
        """Naive relevance selection using id/name/description substring match."""
        normalized_query = query.strip().lower()
        if not normalized_query:
            return self.list_skills()[: max(1, limit)]

        terms = [term for term in normalized_query.split() if term]
        scored: list[tuple[int, Skill]] = []
        for skill in self._skills:
            haystack = " ".join(
                [
                    skill.id,
                    skill.name,
                    skill.description or "",
                    skill.content or "",
                ]
            ).lower()
            # Prefer exact phrase matches, then token coverage.
            phrase_score = 10 if normalized_query in haystack else 0
            term_score = sum(1 for term in terms if term in haystack)
            score = phrase_score + term_score
            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda item: (-item[0], item[1].id))
        result = [skill for _, skill in scored]
        if not result:
            result = list(self._skills)
        return result[: max(1, limit)]


__all__ = ["SkillStore"]
