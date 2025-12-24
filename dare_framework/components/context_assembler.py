from __future__ import annotations

from dataclasses import dataclass

from dare_framework.components.interfaces import IContextAssembler
from dare_framework.core.models import AssembledContext, MemoryItem, Milestone, MilestoneContext, RunContext


@dataclass
class DefaultContextAssembler(IContextAssembler):
    async def assemble(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> AssembledContext:
        return AssembledContext(
            milestone_description=milestone.description,
            reflections=milestone_ctx.reflections,
            previous_summaries=[],
            memory_items=[],
            additional_context={"milestone_id": milestone.milestone_id},
        )

    async def compress(self, context: AssembledContext, max_tokens: int) -> AssembledContext:
        return context
