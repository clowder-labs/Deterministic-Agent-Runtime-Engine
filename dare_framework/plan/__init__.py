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
    ProposedPlan,
    ProposedStep,
    RunResult,
    Task,
    ToolLoopRequest,
    ValidatedPlan,
    ValidatedStep,
    VerifyResult,
)
from dare_framework.plan._internal.default_planner import DefaultPlanner
from dare_framework.plan._internal.default_remediator import DefaultRemediator

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
    "ProposedPlan",
    "ProposedStep",
    "RunResult",
    "Task",
    "ToolLoopRequest",
    "ValidatedPlan",
    "ValidatedStep",
    "VerifyResult",
    # Default implementations
    "DefaultPlanner",
    "DefaultRemediator",
]

