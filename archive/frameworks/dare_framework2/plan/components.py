"""Plan domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dare_framework2.context.types import AssembledContext
    from dare_framework2.plan.types import (
        ProposedPlan,
        ValidatedPlan,
        ExecuteResult,
        VerifyResult,
    )


@runtime_checkable
class IPlanner(Protocol):
    """Planning strategy interface.
    
    Responsible for generating execution plans from the current context.
    The planner's output is untrusted and must be validated before execution.
    """

    async def plan(self, ctx: "AssembledContext") -> "ProposedPlan":
        """Generate a plan from the assembled context.
        
        Args:
            ctx: The assembled context containing task info and history
            
        Returns:
            A proposed plan (untrusted, needs validation)
        """
        ...


@runtime_checkable
class IValidator(Protocol):
    """Validation strategy interface.
    
    Responsible for:
    1. Validating proposed plans (deriving trusted fields from registries)
    2. Verifying milestone execution results
    """

    async def validate_plan(
        self,
        plan: "ProposedPlan",
        ctx: dict[str, Any],
    ) -> "ValidatedPlan":
        """Validate a proposed plan.
        
        Derives trusted security fields from capability registries
        and checks that all referenced capabilities exist.
        
        Args:
            plan: The proposed plan from the planner
            ctx: Current runtime context
            
        Returns:
            A validated plan (or failed validation with errors)
        """
        ...

    async def verify_milestone(
        self,
        result: "ExecuteResult",
        ctx: dict[str, Any],
    ) -> "VerifyResult":
        """Verify that a milestone was successfully completed.
        
        Args:
            result: The execution result to verify
            ctx: Current runtime context
            
        Returns:
            Verification result with success status and evidence
        """
        ...


@runtime_checkable
class IRemediator(Protocol):
    """Remediation strategy interface.
    
    Responsible for generating reflection/remediation guidance
    when verification fails, to help the next planning attempt.
    """

    async def remediate(
        self,
        verify_result: "VerifyResult",
        ctx: dict[str, Any],
    ) -> str:
        """Generate remediation guidance for a failed verification.
        
        Args:
            verify_result: The failed verification result
            ctx: Current runtime context
            
        Returns:
            Reflection/guidance string for the next attempt
        """
        ...
