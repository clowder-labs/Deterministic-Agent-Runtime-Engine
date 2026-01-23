"""hook domain types."""

from __future__ import annotations

from enum import Enum


class HookPhase(Enum):
    """Hook phases for lifecycle events (v4.0-aligned)."""

    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"
    BEFORE_PLAN = "before_plan"
    AFTER_PLAN = "after_plan"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_VERIFY = "before_verify"
    AFTER_VERIFY = "after_verify"


__all__ = ["HookPhase"]
