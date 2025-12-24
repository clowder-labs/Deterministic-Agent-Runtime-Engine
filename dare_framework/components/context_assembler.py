from __future__ import annotations

from ..core.interfaces import IContextAssembler
from ..core.models import AssembledContext, Message, Milestone, MilestoneContext, RunContext


class BasicContextAssembler(IContextAssembler):
    async def assemble(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> AssembledContext:
        return AssembledContext(messages=[Message(role="system", content=milestone.description)])

    async def compress(self, context: AssembledContext, max_tokens: int) -> AssembledContext:
        return context
