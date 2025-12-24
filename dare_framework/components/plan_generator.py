from __future__ import annotations

from dataclasses import dataclass

from dare_framework.components.interfaces import IPlanGenerator
from dare_framework.core.models import Milestone, MilestoneContext, ProposedPlan, ProposedStep, RunContext


@dataclass
class DefaultPlanGenerator(IPlanGenerator):
    tool_name: str = "noop"

    async def generate_plan(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        plan_attempts: list[dict],
        ctx: RunContext,
    ) -> ProposedPlan:
        description = f"Handle milestone: {milestone.description}"
        step = ProposedStep(
            step_id=f"{milestone.milestone_id}_step_1",
            tool_name=self.tool_name,
            tool_input={"message": milestone.description},
            description="Perform a no-op action to mark progress.",
        )
        return ProposedPlan(plan_description=description, proposed_steps=[step])
