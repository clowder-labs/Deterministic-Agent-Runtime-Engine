from __future__ import annotations

from collections.abc import Sequence

from dare_framework.contracts.ids import generator_id
from dare_framework.context.types import AssembledContext
from dare_framework.plan.planning import ProposedPlan, ProposedStep
from dare_framework.plan.components import IPlanner


class DeterministicPlanner(IPlanner):
    """A deterministic planner used for tests and examples.

    Each call to plan() returns the next configured step list. When steps are exhausted,
    it reuses the last plan.
    """

    def __init__(self, plans: Sequence[Sequence[ProposedStep]]) -> None:
        self._plans = [list(steps) for steps in plans]
        self._call_count = 0

    async def plan(self, ctx: AssembledContext) -> ProposedPlan:
        index = min(self._call_count, max(0, len(self._plans) - 1))
        self._call_count += 1
        steps = self._plans[index] if self._plans else []
        if not steps:
            steps = [
                ProposedStep(
                    step_id=generator_id("step"),
                    capability_id="tool:noop",
                    params={},
                    description="noop",
                )
            ]
        return ProposedPlan(plan_description=_default_description(ctx), steps=steps, attempt=self._call_count - 1)


def _default_description(ctx: AssembledContext) -> str:
    user_messages = [msg.content for msg in ctx.messages if msg.role == "user"]
    if user_messages:
        return user_messages[-1]
    return "deterministic plan"
