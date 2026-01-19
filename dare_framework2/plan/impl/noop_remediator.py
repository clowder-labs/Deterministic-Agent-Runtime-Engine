"""No-op remediator implementation."""

from __future__ import annotations

from typing import Any

from dare_framework2.plan.interfaces import IRemediator
from dare_framework2.plan.types import VerifyResult


class NoOpRemediator(IRemediator):
    """A minimal remediator that turns verification errors into a reflection string.
    
    Simply joins error messages into a single string for the next
    planning attempt.
    """

    async def remediate(
        self,
        verify_result: VerifyResult,
        ctx: dict[str, Any],
    ) -> str:
        """Generate a simple reflection from verification errors."""
        if verify_result.success:
            return "no-op"
        return (
            "; ".join(verify_result.errors)
            if verify_result.errors
            else "remediation required"
        )
