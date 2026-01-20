"""Plan domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dare_framework3.context.types import AssembledContext
    from dare_framework3.plan.types import ProposedPlan, ValidatedPlan, ExecuteResult, VerifyResult


@runtime_checkable
class IPlanner(Protocol):
    """Planning strategy interface."""

    async def plan(self, ctx: "AssembledContext") -> "ProposedPlan":
        ...


@runtime_checkable
class IValidator(Protocol):
    """Validation strategy interface."""

    async def validate_plan(
        self,
        plan: "ProposedPlan",
        ctx: dict[str, Any],
    ) -> "ValidatedPlan":
        ...

    async def verify_milestone(
        self,
        result: "ExecuteResult",
        ctx: dict[str, Any],
    ) -> "VerifyResult":
        ...


@runtime_checkable
class IRemediator(Protocol):
    """Remediation strategy interface."""

    async def remediate(
        self,
        verify_result: "VerifyResult",
        ctx: dict[str, Any],
    ) -> str:
        ...


__all__ = ["IPlanner", "IValidator", "IRemediator"]
