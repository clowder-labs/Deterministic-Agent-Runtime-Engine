"""Prompt enricher: merge skill content into system prompt."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from dare_framework.model.types import Prompt

if TYPE_CHECKING:
    from dare_framework.skill.types import Skill


def enrich_prompt_with_skills(base_prompt: Prompt, skill_paths: list[str] | list[Path]) -> Prompt:
    """Merge skill content into base prompt.

    Loads skills from paths via FileSystemSkillLoader, appends skill sections
    to the base prompt content.
    """
    from dare_framework.skill._internal.filesystem_skill_loader import FileSystemSkillLoader

    loader = FileSystemSkillLoader(*[Path(p) for p in skill_paths])
    skills = loader.load()
    if not skills:
        return base_prompt

    sections: list[str] = [base_prompt.content]
    for skill in skills:
        sections.append(skill.to_context_section())

    merged_content = "\n\n---\n\n".join(sections)
    return Prompt(
        prompt_id=base_prompt.prompt_id,
        role=base_prompt.role,
        content=merged_content,
        supported_models=base_prompt.supported_models,
        order=base_prompt.order,
    )


def enrich_prompt_with_skill(base_prompt: Prompt, skill: Skill) -> Prompt:
    """Append a single skill section and scripts block to base prompt."""
    sections: list[str] = [base_prompt.content, skill.to_context_section()]
    merged_content = "\n\n---\n\n".join(sections)
    return Prompt(
        prompt_id=base_prompt.prompt_id,
        role=base_prompt.role,
        content=merged_content,
        supported_models=base_prompt.supported_models,
        order=base_prompt.order,
    )


def enrich_prompt_with_skill_summaries(base_prompt: Prompt, skills: list[Skill]) -> Prompt:
    """Append brief catalog of skills (id, name, description) for auto_skill_mode. Use search_skill(skill_id) to load full content into dict; assemble merges dict into context for next LLM input."""
    if not skills:
        return base_prompt
    lines: list[str] = [
        "",
        "## Available skills (brief catalog)",
        "Use the tool search_skill(skill_id) to load the full instructions for a skill; then assemble will add that content to context for the next LLM call.",
        "",
    ]
    for s in skills:
        lines.append(f"- **{s.id}** — {s.name}: {s.description or '(no description)'}")
    catalog = "\n".join(lines)
    merged_content = base_prompt.content.rstrip() + "\n\n" + catalog.strip()
    return Prompt(
        prompt_id=base_prompt.prompt_id,
        role=base_prompt.role,
        content=merged_content,
        supported_models=base_prompt.supported_models,
        order=base_prompt.order,
    )


__all__ = ["enrich_prompt_with_skill", "enrich_prompt_with_skills", "enrich_prompt_with_skill_summaries"]
