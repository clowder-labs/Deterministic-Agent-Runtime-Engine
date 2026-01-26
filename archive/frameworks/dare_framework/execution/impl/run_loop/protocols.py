"""Kernel run loop protocols (v2)."""

from __future__ import annotations

from typing import Protocol

from dare_framework.plan.results import RunResult
from dare_framework.execution.impl.run_loop.models import RunLoopState, TickResult


class IRunLoop(Protocol):
    """Tick-based run surface for the Kernel (v2.0)."""

    @property
    def state(self) -> RunLoopState: ...

    async def tick(self) -> TickResult:
        """Execute a minimal scheduling step to enable debugging/visualization."""

    async def run(self, task: "Task") -> RunResult:
        """Drive execution until termination (internally calls tick repeatedly)."""
