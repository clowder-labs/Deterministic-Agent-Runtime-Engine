"""Plan- and loop-related canonical types (v2.0).

This package contains the types that flow through the five-layer loop:
- Task/Milestone
- Proposed/Validated plans
- Envelope/DonePredicate
- Execute/Verify/Run results
"""

from dare_framework.core.plan.envelope import DonePredicate, Envelope, EvidenceCondition, ToolLoopRequest
from dare_framework.core.plan.planning import ProposedPlan, ProposedStep, ValidatedPlan, ValidatedStep
from dare_framework.core.plan.results import (
    ExecuteResult,
    MilestoneResult,
    MilestoneSummary,
    RunResult,
    SessionSummary,
    ToolLoopResult,
    VerifyResult,
)
from dare_framework.core.plan.task import Milestone, Task

__all__ = [
    "DonePredicate",
    "Envelope",
    "EvidenceCondition",
    "ToolLoopRequest",
    "ProposedPlan",
    "ProposedStep",
    "ValidatedPlan",
    "ValidatedStep",
    "ExecuteResult",
    "MilestoneResult",
    "MilestoneSummary",
    "RunResult",
    "SessionSummary",
    "ToolLoopResult",
    "VerifyResult",
    "Milestone",
    "Task",
]
