"""hook domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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

    @property
    def is_before_phase(self) -> bool:
        """Whether this phase runs before the corresponding runtime action."""

        return self.value.startswith("before_")


class HookDecision(Enum):
    """Governance decision returned by hook dispatch."""

    ALLOW = "allow"
    BLOCK = "block"
    ASK = "ask"


@dataclass(frozen=True)
class HookEnvelope:
    """Typed hook payload envelope used by governed hook dispatch."""

    hook_version: int
    phase: str
    invocation_id: str
    context_id: str
    timestamp_ms: int
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HookResult:
    """Normalized hook result contract for governance decisions."""

    decision: HookDecision
    patch: dict[str, Any] | None = None
    message: str | None = None


__all__ = ["HookDecision", "HookEnvelope", "HookPhase", "HookResult"]
