"""Plan domain: how to plan and verify execution.

This domain handles the planning, validation, and verification
of agent execution, implementing the core Plan-Execute-Verify loop.

Factory Functions:
    create_default_planner: Create default IPlanner
    create_default_validator: Create default IValidator
    create_default_remediator: Create default IRemediator
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework3.plan.interfaces import IPlanner, IValidator, IRemediator
from dare_framework3.plan.types import (
    # Task and Milestone
    Task,
    Milestone,
    # Plan proposals
    ProposedStep,
    ProposedPlan,
    # Validated plans
    ValidatedStep,
    ValidatedPlan,
    # Envelope and predicates
    Envelope,
    DonePredicate,
    EvidenceCondition,
    ToolLoopRequest,
    # Results
    ToolLoopResult,
    ExecuteResult,
    VerifyResult,
    MilestoneResult,
    MilestoneSummary,
    SessionSummary,
    RunResult,
)

if TYPE_CHECKING:
    from dare_framework3.tool.interfaces import IToolGateway

__all__ = [
    # Interfaces
    "IPlanner",
    "IValidator",
    "IRemediator",
    # Task and Milestone
    "Task",
    "Milestone",
    # Plan proposals
    "ProposedStep",
    "ProposedPlan",
    # Validated plans
    "ValidatedStep",
    "ValidatedPlan",
    # Envelope and predicates
    "Envelope",
    "DonePredicate",
    "EvidenceCondition",
    "ToolLoopRequest",
    # Results
    "ToolLoopResult",
    "ExecuteResult",
    "VerifyResult",
    "MilestoneResult",
    "MilestoneSummary",
    "SessionSummary",
    "RunResult",
    # Factory functions
    "create_default_planner",
    "create_default_validator",
    "create_default_remediator",
]


# =============================================================================
# Factory Functions
# =============================================================================

def create_default_planner() -> IPlanner:
    """Create the default IPlanner implementation.
    
    Returns:
        A DeterministicPlanner instance with empty steps
    """
    from dare_framework3.plan.impl.deterministic_planner import DeterministicPlanner
    return DeterministicPlanner([])


def create_default_validator(
    tool_gateway: "IToolGateway | None" = None,
) -> IValidator:
    """Create the default IValidator implementation.
    
    Args:
        tool_gateway: Tool gateway for capability validation
        
    Returns:
        A GatewayValidator or CompositeValidator instance
    """
    from dare_framework3.plan.impl.gateway_validator import GatewayValidator
    return GatewayValidator(tool_gateway)


def create_default_remediator() -> IRemediator:
    """Create the default IRemediator implementation.
    
    Returns:
        A NoOpRemediator instance
    """
    from dare_framework3.plan.impl.noop_remediator import NoOpRemediator
    return NoOpRemediator()
