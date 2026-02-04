"""Skill domain - Claude Code / Agent Skills support."""

from dare_framework.skill.kernel import ISkill, ISkillTool
from dare_framework.skill.interfaces import ISkillLoader, ISkillSelector, ISkillStore
from dare_framework.skill.types import Skill

__all__ = [
    "Skill",
    "ISkill",
    "ISkillLoader",
    "ISkillStore",
    "ISkillSelector",
    "ISkillTool",
]
