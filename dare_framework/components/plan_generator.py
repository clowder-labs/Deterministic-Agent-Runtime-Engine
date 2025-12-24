from __future__ import annotations

from typing import Any, Iterable

from ..core.interfaces import IPlanGenerator
from ..core.models import Milestone, MilestoneContext, ProposedPlan, ProposedStep, RunContext, new_id


class DeterministicPlanGenerator(IPlanGenerator):
    def __init__(self, plans: Iterable[list[ProposedStep]]):
        self._plans = list(plans)

    async def generate_plan(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        plan_attempts: list[dict[str, Any]],
        ctx: RunContext,
    ) -> ProposedPlan:
        attempt = len(plan_attempts)
        index = min(attempt, len(self._plans) - 1)
        steps = self._plans[index] if self._plans else []
        if not steps:
            steps = [
                ProposedStep(
                    step_id=new_id("step"),
                    tool_name="noop",
                    tool_input={},
                    description=milestone.description,
                )
            ]
        return ProposedPlan(
            plan_description=milestone.description,
            proposed_steps=steps,
            attempt=attempt,
        )
