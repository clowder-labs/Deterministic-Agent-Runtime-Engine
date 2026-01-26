"""plan domain types (task/plan/result/envelope).

Scope:
- Provide minimal data models for the current interface surface.
- This is not a full runtime implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dare_framework.context.types import Budget
from dare_framework.security.types import RiskLevel


@dataclass(frozen=True)
class Task:
    """A high-level execution request."""

    description: str
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    """Top-level execution result returned to developers."""

    success: bool
    output: Any | None = None
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProposedPlan:
    """Untrusted plan proposal produced by a planner."""

    plan_description: str
    steps: list["ProposedStep"] = field(default_factory=list)
    attempt: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidatedPlan:
    """Trusted plan derived from registries and policy/trust checks."""

    plan_description: str
    steps: list["ValidatedStep"] = field(default_factory=list)
    success: bool = True
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerifyResult:
    """Verification output for a milestone."""

    success: bool
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DonePredicate:
    """Defines what 'done' means for a Tool Loop attempt."""

    required_keys: list[str] = field(default_factory=list)
    description: str | None = None


@dataclass(frozen=True)
class Envelope:
    """Execution boundary for the Tool Loop."""

    allowed_capability_ids: list[str] = field(default_factory=list)
    budget: Budget = field(default_factory=Budget)
    done_predicate: DonePredicate | None = None
    risk_level: RiskLevel = RiskLevel.READ_ONLY


@dataclass(frozen=True)
class ProposedStep:
    """Untrusted step proposal produced by the planner."""

    step_id: str
    capability_id: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    envelope: Envelope | None = None


@dataclass(frozen=True)
class ValidatedStep:
    """Trusted step derived from registries and policy/trust checks."""

    step_id: str
    capability_id: str
    risk_level: RiskLevel
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    envelope: Envelope | None = None


@dataclass(frozen=True)
class ToolLoopRequest:
    """Tool Loop invocation payload (capability id + params + envelope boundary)."""

    capability_id: str
    params: dict[str, Any] = field(default_factory=dict)
    envelope: Envelope = field(default_factory=Envelope)


__all__ = [
    "DonePredicate",
    "Envelope",
    "ProposedStep",
    "ProposedPlan",
    "RunResult",
    "Task",
    "ToolLoopRequest",
    "ValidatedStep",
    "ValidatedPlan",
    "VerifyResult",
]
