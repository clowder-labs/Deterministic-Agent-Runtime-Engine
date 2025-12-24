from __future__ import annotations

from ..core.interfaces import IRemediator
from ..core.models import RunContext, VerifyResult


class NoOpRemediator(IRemediator):
    async def remediate(self, verify_result: VerifyResult, errors: list[str], ctx: RunContext) -> str:
        if not errors:
            return "no-op"
        return "; ".join(errors)
