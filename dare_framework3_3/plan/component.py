"""Plan domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dare_framework3_3.context.types import AssembledContext
    from dare_framework3_3.plan.types import ProposedPlan, ValidatedPlan, ExecuteResult, VerifyResult


@runtime_checkable
class IPlanner(Protocol):
    """[Component] Planning strategy interface.

    Usage: Called by the agent to propose a plan for the current context.
    """

    async def plan(self, ctx: "AssembledContext") -> "ProposedPlan":
        """[Component] Produce a proposed plan from the assembled context."""
        ...


@runtime_checkable
class IValidator(Protocol):
    """[Component] Validation strategy interface.

    Usage: Called by the agent to validate plans and milestones.
    """

    async def validate_plan(
        self,
        plan: "ProposedPlan",
        ctx: dict[str, Any],
    ) -> "ValidatedPlan":
        """[Component] Validate a proposed plan."""
        ...

    async def verify_milestone(
        self,
        result: "ExecuteResult",
        ctx: dict[str, Any],
    ) -> "VerifyResult":
        """[Component] Verify milestone execution results."""
        ...


@runtime_checkable
class IRemediator(Protocol):
    """[Component] Remediation strategy interface.

    Usage: Called by the agent to derive next-step guidance after failures.
    """

    async def remediate(
        self,
        verify_result: "VerifyResult",
        ctx: dict[str, Any],
    ) -> str:
        """[Component] Produce remediation guidance from verification results."""
        ...


__all__ = ["IPlanner", "IValidator", "IRemediator"]
