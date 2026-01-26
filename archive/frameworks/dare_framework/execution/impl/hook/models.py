"""Kernel hook models (v2)."""

from __future__ import annotations

from enum import Enum


class HookPhase(Enum):
    """Kernel hook phases (v2.0)."""

    BEFORE_PLAN = "before_plan"
    AFTER_PLAN = "after_plan"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_VERIFY = "before_verify"
    AFTER_VERIFY = "after_verify"
    ON_EVENT = "on_event"

