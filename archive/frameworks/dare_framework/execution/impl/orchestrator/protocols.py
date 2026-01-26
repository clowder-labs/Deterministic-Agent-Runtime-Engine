"""Kernel orchestrator protocols (v2)."""

from __future__ import annotations

from typing import Protocol

from dare_framework.plan.envelope import ToolLoopRequest
from dare_framework.plan.planning import ValidatedPlan
from dare_framework.plan.results import ExecuteResult, MilestoneResult, RunResult, ToolLoopResult
from dare_framework.plan.task import Milestone, Task


class ILoopOrchestrator(Protocol):
    """Five-layer loop skeleton (v2.0)."""

    async def run_session_loop(self, task: Task) -> RunResult: ...

    async def run_milestone_loop(self, milestone: Milestone) -> MilestoneResult: ...

    async def run_plan_loop(self, milestone: Milestone) -> ValidatedPlan: ...

    async def run_execute_loop(self, plan: ValidatedPlan) -> ExecuteResult: ...

    async def run_tool_loop(self, req: ToolLoopRequest) -> ToolLoopResult: ...

