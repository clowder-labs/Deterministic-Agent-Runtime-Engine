"""Skill components (Layer 2), loaded via the `dare_framework.v2.skills` entrypoint group."""

from dare_framework.components.skills.noop import NoOpSkill
from dare_framework.components.skills.protocols import ISkill

__all__ = [
    "ISkill",
    "NoOpSkill",
]
