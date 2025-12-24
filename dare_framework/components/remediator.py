from __future__ import annotations

from dataclasses import dataclass

from dare_framework.components.interfaces import IRemediator
from dare_framework.core.models import MilestoneContext, RunContext, ToolError, VerifyResult


@dataclass
class DefaultRemediator(IRemediator):
    async def remediate(
        self,
        verify_result: VerifyResult,
        tool_errors: list[ToolError],
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> str:
        base_reason = verify_result.failure_reason or "unknown_failure"
        error_count = len(tool_errors)
        return f"Verification failed: {base_reason}. Tool errors: {error_count}."
