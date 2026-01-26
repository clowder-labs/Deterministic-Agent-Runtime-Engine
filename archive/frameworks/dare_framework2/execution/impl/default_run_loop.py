"""Default run loop implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework2.execution.kernel import IRunLoop, ILoopOrchestrator
from dare_framework2.execution.types import RunLoopState, TickResult
from dare_framework2.plan.types import RunResult

if TYPE_CHECKING:
    from dare_framework2.plan.types import Task


class DefaultRunLoop(IRunLoop):
    """A minimal tick-based run loop wrapping the orchestrator.
    
    MVP implementation that executes the full session loop in one tick.
    More granular stepping can be added later.
    
    Args:
        orchestrator: The loop orchestrator to use
    """

    def __init__(self, orchestrator: ILoopOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._state = RunLoopState.IDLE
        self._pending_task: Task | None = None
        self._result: RunResult | None = None

    @property
    def state(self) -> RunLoopState:
        """Current run loop state."""
        return self._state

    async def tick(self) -> TickResult:
        """Execute a scheduling tick.
        
        MVP: Executes the full session loop in one tick.
        """
        if self._pending_task is None:
            completed = self._state in {RunLoopState.COMPLETED, RunLoopState.ABORTED}
            return TickResult(
                state=self._state,
                produced_event_ids=[],
                completed=completed,
            )

        # Execute full session loop
        self._state = RunLoopState.EXECUTING
        result = await self._orchestrator.run_session_loop(self._pending_task)
        self._result = result
        self._pending_task = None
        self._state = RunLoopState.COMPLETED if result.success else RunLoopState.ABORTED
        
        return TickResult(
            state=self._state,
            produced_event_ids=[],
            completed=True,
        )

    async def run(self, task: "Task") -> RunResult:
        """Run a task to completion."""
        self._pending_task = task
        self._result = None
        self._state = RunLoopState.PLANNING
        
        tick = await self.tick()
        
        if not tick.completed or self._result is None:
            self._state = RunLoopState.ABORTED
            return RunResult(success=False, errors=["run did not complete"])
        
        return self._result
