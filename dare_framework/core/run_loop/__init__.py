from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from dare_framework.core.plan.results import RunResult


class RunLoopState(Enum):
    """Tick-based run loop states (v2.0)."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    PAUSED = "paused"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass(frozen=True)
class TickResult:
    """Result of a single scheduling tick (debug/visualization friendly)."""

    state: RunLoopState
    produced_event_ids: list[str] = field(default_factory=list)
    completed: bool = False


class IRunLoop(Protocol):
    """Tick-based run surface for the Kernel (v2.0)."""

    @property
    def state(self) -> RunLoopState: ...

    async def tick(self) -> TickResult:
        """Execute a minimal scheduling step to enable debugging/visualization."""

    async def run(self, task: "Task") -> RunResult:
        """Drive execution until termination (internally calls tick repeatedly)."""
