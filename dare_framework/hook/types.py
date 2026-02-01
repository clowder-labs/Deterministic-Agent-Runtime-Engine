"""hook domain types."""

from __future__ import annotations

from enum import Enum


class HookPhase(Enum):
    """Hook phases for lifecycle events."""

    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"
    BEFORE_SESSION = "before_session"
    AFTER_SESSION = "after_session"
    BEFORE_MILESTONE = "before_milestone"
    AFTER_MILESTONE = "after_milestone"
    BEFORE_PLAN = "before_plan"
    AFTER_PLAN = "after_plan"
    BEFORE_EXECUTE = "before_execute"
    AFTER_EXECUTE = "after_execute"
    BEFORE_CONTEXT_ASSEMBLE = "before_context_assemble"
    AFTER_CONTEXT_ASSEMBLE = "after_context_assemble"
    BEFORE_MODEL = "before_model"
    AFTER_MODEL = "after_model"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_VERIFY = "before_verify"
    AFTER_VERIFY = "after_verify"


__all__ = ["HookPhase"]
