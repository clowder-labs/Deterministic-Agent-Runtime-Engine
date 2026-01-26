"""Plan domain component interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework.context.types import AssembledContext
from dare_framework.plan.planning import ProposedPlan, ValidatedPlan
from dare_framework.plan.results import ExecuteResult, VerifyResult


@runtime_checkable
class IPlanner(Protocol):
    """Planning strategy interface (Layer 2)."""

    async def plan(self, ctx: AssembledContext) -> ProposedPlan: ...


@runtime_checkable
class IValidator(Protocol):
    """Validation strategy interface (Layer 2)."""

    async def validate_plan(self, plan: ProposedPlan, ctx: dict) -> ValidatedPlan: ...

    async def verify_milestone(self, result: ExecuteResult, ctx: dict) -> VerifyResult: ...


@runtime_checkable
class IRemediator(Protocol):
    """Remediation strategy interface (Layer 2)."""

    async def remediate(self, verify_result: VerifyResult, ctx: dict) -> str: ...


__all__ = ["IPlanner", "IValidator", "IRemediator"]
