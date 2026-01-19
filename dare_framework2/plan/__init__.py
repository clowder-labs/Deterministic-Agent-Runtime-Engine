"""Plan domain: how to plan and verify execution.

This domain handles the planning, validation, and verification
of agent execution, implementing the core Plan-Execute-Verify loop.
"""

from dare_framework2.plan.interfaces import IPlanner, IValidator, IRemediator
from dare_framework2.plan.types import (
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
]
