"""Hook domain data types."""

from __future__ import annotations

from enum import Enum


class HookPhase(Enum):
    """Kernel hook phases for extension points.
    
    Values:
        BEFORE_PLAN: Before planning starts
        AFTER_PLAN: After planning completes
        BEFORE_TOOL: Before tool execution
        AFTER_TOOL: After tool execution
        BEFORE_VERIFY: Before verification
        AFTER_VERIFY: After verification
    """
    BEFORE_PLAN = "before_plan"
    AFTER_PLAN = "after_plan"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_VERIFY = "before_verify"
    AFTER_VERIFY = "after_verify"
