"""Keyword-based skill selector for task relevance."""

from __future__ import annotations

import re

from dare_framework.skill.types import Skill


class KeywordSkillSelector:
    """Selects skills by matching task description keywords against skill metadata."""

    def __init__(self, *, min_score: float = 0.0) -> None:
        """Initialize selector.

        Args:
            min_score: Minimum match score (0–1) for a skill to be included.
        """
        self._min_score = min_score

    def select(self, task_description: str, skills: list[Skill]) -> list[Skill]:
        """Select skills whose name/description overlap with task keywords."""
        if not task_description or not skills:
            return []

        task_words = self._tokenize(task_description.lower())
        if not task_words:
            return []

        scored: list[tuple[float, Skill]] = []
        for skill in skills:
            score = self._score(skill, task_words)
            if score >= self._min_score:
                scored.append((score, skill))

        scored.sort(key=lambda x: -x[0])
        return [s for _, s in scored]

    def _tokenize(self, text: str) -> set[str]:
        """Extract meaningful tokens (words)."""
        words = re.findall(r"[a-z0-9]+", text.lower())
        return {w for w in words if len(w) > 1}

    def _score(self, skill: Skill, task_words: set[str]) -> float:
        """Score skill relevance to task (0–1)."""
        skill_text = f"{skill.name} {skill.description}".lower()
        skill_words = self._tokenize(skill_text)
        if not skill_words:
            return 0.0
        overlap = len(task_words & skill_words) / len(task_words)
        return min(1.0, overlap)


__all__ = ["KeywordSkillSelector"]
