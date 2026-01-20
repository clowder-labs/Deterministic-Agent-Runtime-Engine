"""Plan domain: planning, validation, and remediation.

This domain handles task planning, plan validation,
milestone verification, and remediation strategies.
"""

from __future__ import annotations

# Protocol (for type annotations and custom implementations)
from dare_framework3_2.plan.component import IPlanner, IValidator, IRemediator

# Common types
from dare_framework3_2.plan.types import (
    Task,
    Milestone,
    RunResult,
    Envelope,
    SessionSummary,
    MilestoneResult,
)

# Default implementations
from dare_framework3_2.plan.impl.deterministic_planner import DeterministicPlanner
from dare_framework3_2.plan.impl.composite_validator import CompositeValidator
from dare_framework3_2.plan.impl.gateway_validator import GatewayValidator
from dare_framework3_2.plan.impl.noop_remediator import NoOpRemediator

__all__ = [
    # Protocol
    "IPlanner",
    "IValidator",
    "IRemediator",
    # Types
    "Task",
    "Milestone",
    "RunResult",
    "Envelope",
    "SessionSummary",
    "MilestoneResult",
    # Implementations
    "DeterministicPlanner",
    "CompositeValidator",
    "GatewayValidator",
    "NoOpRemediator",
]
