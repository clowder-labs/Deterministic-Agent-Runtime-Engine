from __future__ import annotations

from dare_framework.core.orchestrator import ILoopOrchestrator
from dare_framework.core.plan.results import RunResult
from dare_framework.core.run_loop import IRunLoop, RunLoopState, TickResult
from dare_framework.core.plan.task import Task


class DefaultRunLoop(IRunLoop):
    """A minimal tick-based run loop wrapping the orchestrator (v2.0 MVP)."""

    def __init__(self, orchestrator: ILoopOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._state = RunLoopState.IDLE
        self._pending_task: Task | None = None
        self._result: RunResult | None = None

    @property
    def state(self) -> RunLoopState:
        return self._state

    async def tick(self) -> TickResult:
        if self._pending_task is None:
            completed = self._state in {RunLoopState.COMPLETED, RunLoopState.ABORTED}
            return TickResult(state=self._state, produced_event_ids=[], completed=completed)

        # MVP tick executes the full session loop. More granular stepping can be added later.
        self._state = RunLoopState.EXECUTING
        result = await self._orchestrator.run_session_loop(self._pending_task)
        self._result = result
        self._pending_task = None
        self._state = RunLoopState.COMPLETED if result.success else RunLoopState.ABORTED
        return TickResult(state=self._state, produced_event_ids=[], completed=True)

    async def run(self, task: Task) -> RunResult:
        self._pending_task = task
        self._result = None
        self._state = RunLoopState.PLANNING
        tick = await self.tick()
        if not tick.completed or self._result is None:
            # The MVP tick is expected to complete the run in one step; treat otherwise as abort.
            self._state = RunLoopState.ABORTED
            return RunResult(success=False, errors=["run did not complete"])
        return self._result
