"""Deterministic planner implementation."""

from __future__ import annotations

from collections.abc import Sequence

from dare_framework3_2.context.types import AssembledContext
from dare_framework3_2.plan.component import IPlanner
from dare_framework3_2.plan.types import ProposedPlan, ProposedStep
from dare_framework3_2.utils.ids import generate_id


class DeterministicPlanner(IPlanner):
    """A deterministic planner for tests and examples.
    
    Returns predefined plan sequences. Each call to plan() returns
    the next configured step list. When steps are exhausted, it
    reuses the last plan.
    
    Args:
        plans: Sequence of plan step sequences to return
    """

    def __init__(self, plans: Sequence[Sequence[ProposedStep]]) -> None:
        self._plans = [list(steps) for steps in plans]
        self._call_count = 0

    async def plan(self, ctx: AssembledContext) -> ProposedPlan:
        """Return the next predefined plan."""
        index = min(self._call_count, max(0, len(self._plans) - 1))
        self._call_count += 1
        steps = self._plans[index] if self._plans else []
        
        # Default to a no-op step if no steps configured
        if not steps:
            steps = [
                ProposedStep(
                    step_id=generate_id("step"),
                    capability_id="tool:noop",
                    params={},
                    description="noop",
                )
            ]
        
        return ProposedPlan(
            plan_description=_default_description(ctx),
            steps=steps,
            attempt=self._call_count - 1,
        )


def _default_description(ctx: AssembledContext) -> str:
    """Extract a description from the context's user messages."""
    user_messages = [msg.content for msg in ctx.messages if msg.role == "user"]
    if user_messages:
        return user_messages[-1]
    return "deterministic plan"
