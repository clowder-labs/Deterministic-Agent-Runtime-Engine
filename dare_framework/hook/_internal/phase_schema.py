"""Per-phase payload schema requirements for governed hook dispatch."""

from __future__ import annotations

from dare_framework.hook.types import HookPhase

_SCHEMAS: dict[HookPhase, dict[str, tuple[str, ...]]] = {
    HookPhase.BEFORE_RUN: {"required": ("task_id", "session_id")},
    HookPhase.AFTER_RUN: {"required": ("success",)},
    HookPhase.BEFORE_SESSION: {"required": ("task_id", "run_id")},
    HookPhase.AFTER_SESSION: {"required": ("success",)},
    HookPhase.BEFORE_MILESTONE: {"required": ("milestone_id",)},
    HookPhase.AFTER_MILESTONE: {"required": ("milestone_id", "success")},
    HookPhase.BEFORE_PLAN: {"required": ("milestone_id", "attempt")},
    HookPhase.AFTER_PLAN: {"required": ("success",)},
    HookPhase.BEFORE_EXECUTE: {"required": tuple()},
    HookPhase.AFTER_EXECUTE: {"required": ("success",)},
    HookPhase.BEFORE_CONTEXT_ASSEMBLE: {"required": tuple()},
    HookPhase.AFTER_CONTEXT_ASSEMBLE: {"required": ("context_length",)},
    HookPhase.BEFORE_MODEL: {"required": tuple()},
    HookPhase.AFTER_MODEL: {"required": tuple()},
    HookPhase.BEFORE_TOOL: {"required": ("tool_name", "tool_call_id", "capability_id")},
    HookPhase.AFTER_TOOL: {"required": ("tool_name", "tool_call_id", "success")},
    HookPhase.BEFORE_VERIFY: {"required": tuple()},
    HookPhase.AFTER_VERIFY: {"required": ("success",)},
}


def schema_for_phase(phase: HookPhase) -> dict[str, tuple[str, ...]]:
    """Return required payload fields for a given hook phase."""

    return _SCHEMAS[phase]


__all__ = ["schema_for_phase"]
