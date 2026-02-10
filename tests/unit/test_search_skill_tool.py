from __future__ import annotations

from pathlib import Path

import pytest

from dare_framework.skill._internal.search_skill_tool import SearchSkillTool
from dare_framework.skill.interfaces import ISkillStore
from dare_framework.skill.types import Skill
from dare_framework.tool.types import RunContext


class StaticSkillStore(ISkillStore):
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = list(skills)
        self._index = {skill.id: skill for skill in self._skills}

    def list_skills(self) -> list[Skill]:
        return list(self._skills)

    def get_skill(self, skill_id: str) -> Skill | None:
        return self._index.get(skill_id)

    def select_for_task(self, query: str, limit: int = 5) -> list[Skill]:
        lowered = query.strip().lower()
        matches = []
        for skill in self._skills:
            haystack = f"{skill.id} {skill.name} {skill.description} {skill.content}".lower()
            if lowered and lowered in haystack:
                matches.append(skill)
        return matches[: max(1, limit)]


def _skills() -> list[Skill]:
    return [
        Skill(
            id="commit",
            name="Commit Skill",
            description="Create clean commits with clear messages.",
            content="commit content",
            skill_dir=Path("/tmp/commit"),
        ),
        Skill(
            id="review-pr",
            name="Review PR Skill",
            description="Review pull requests with bug-first feedback.",
            content="review content",
            skill_dir=Path("/tmp/review"),
        ),
    ]


def test_search_skill_tool_schema_matches_claude_shape() -> None:
    tool = SearchSkillTool(StaticSkillStore(_skills()))

    schema = tool.input_schema
    assert schema["required"] == ["skill"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"].keys()) == {"skill", "args"}


def test_search_skill_tool_description_includes_available_skills() -> None:
    tool = SearchSkillTool(StaticSkillStore(_skills()))

    description = tool.description
    assert "Available skills:" in description
    assert "- commit (Commit Skill):" in description
    assert "- review-pr (Review PR Skill):" in description


def test_search_skill_tool_description_caps_list_to_50_skills() -> None:
    many_skills = [
        Skill(
            id=f"skill-{index:02d}",
            name=f"Skill {index:02d}",
            description=f"description {index:02d}",
            content=f"content {index:02d}",
        )
        for index in range(52)
    ]
    tool = SearchSkillTool(StaticSkillStore(many_skills))

    description = tool.description
    assert "- skill-00 (Skill 00):" in description
    assert "- skill-49 (Skill 49):" in description
    assert "- skill-50 (Skill 50):" not in description
    assert "- skill-51 (Skill 51):" not in description
    assert "- ... 2 additional skills are not loaded into this description." in description


@pytest.mark.asyncio
async def test_search_skill_tool_resolves_by_skill_name() -> None:
    tool = SearchSkillTool(StaticSkillStore(_skills()))

    result = await tool.execute(
        run_context=RunContext(),
        skill="/commit",
        args="-m 'fix bug'",
    )

    assert result.success is True
    assert result.output["skill_id"] == "commit"
    assert result.output["name"] == "Commit Skill"
    assert result.output["args"] == "-m 'fix bug'"
    assert "## Skill: Commit Skill" in result.output["prompt"]
