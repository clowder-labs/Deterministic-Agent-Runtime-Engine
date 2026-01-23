"""plan domain pluggable interfaces (strategies)."""

from __future__ import annotations

from typing import Protocol

from dare_framework3_4.context.kernel import IContext
from dare_framework3_4.plan.types import ProposedPlan, RunResult, ValidatedPlan, VerifyResult


class IPlanner(Protocol):
    async def plan(self, ctx: IContext) -> ProposedPlan: ...


class IValidator(Protocol):
    async def validate_plan(self, plan: ProposedPlan, ctx: IContext) -> ValidatedPlan: ...

    async def verify_milestone(self, result: RunResult, ctx: IContext) -> VerifyResult: ...


class IRemediator(Protocol):
    async def remediate(self, verify_result: VerifyResult, ctx: IContext) -> str: ...


__all__ = ["IPlanner", "IRemediator", "IValidator"]
