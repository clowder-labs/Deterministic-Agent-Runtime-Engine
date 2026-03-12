"""plan domain facade."""

from dare_framework.plan.interfaces import (
    IPlanner,
    IPlannerManager,
    IRemediator,
    IRemediatorManager,
    IValidator,
    IValidatorManager,
)
from dare_framework.plan.types import (
    DonePredicate,
    Envelope,
    Milestone,
    MilestoneSummary,
    ProposedPlan,
    ProposedStep,
    RunResult,
    SessionSummary,
    Task,
    ToolLoopRequest,
    ValidatedPlan,
    ValidatedStep,
    VerifyResult,
)
from dare_framework.plan.defaults import DefaultPlanner, DefaultRemediator

__all__ = [
    # Interfaces
    "IPlanner",
    "IPlannerManager",
    "IRemediator",
    "IRemediatorManager",
    "IValidator",
    "IValidatorManager",
    # Types
    "DonePredicate",
    "Envelope",
    "Milestone",
    "MilestoneSummary",
    "ProposedPlan",
    "ProposedStep",
    "RunResult",
    "SessionSummary",
    "Task",
    "ToolLoopRequest",
    "ValidatedPlan",
    "ValidatedStep",
    "VerifyResult",
    # Default implementations
    "DefaultPlanner",
    "DefaultRemediator",
]
