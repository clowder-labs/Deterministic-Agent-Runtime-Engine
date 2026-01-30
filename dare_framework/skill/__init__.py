"""Skill domain - Claude Code / Agent Skills support."""

from dare_framework.skill.interfaces import (
    ISkillLoader,
    ISkillSelector,
    ISkillStore,
)
from dare_framework.skill.types import Skill
from dare_framework.skill._internal import (
    FileSystemSkillLoader,
    KeywordSkillSelector,
    SkillScriptRunner,
    SkillStore,
)

__all__ = [
    "Skill",
    "ISkillLoader",
    "ISkillStore",
    "ISkillSelector",
    "FileSystemSkillLoader",
    "KeywordSkillSelector",
    "SkillScriptRunner",
    "SkillStore",
]
