from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from dare_framework.contracts.risk import RiskLevel
from dare_framework.core.plan.envelope import Envelope


@dataclass(frozen=True)
class ProposedStep:
    """Untrusted step proposal produced by the planner (v2.0)."""

    step_id: str
    capability_id: str
    params: dict[str, Any]
    description: str = ""
    envelope: Envelope | None = None


@dataclass(frozen=True)
class ProposedPlan:
    """Untrusted plan proposal produced by the planner (v2.0)."""

    plan_description: str
    steps: list[ProposedStep]
    attempt: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidatedStep:
    """Trusted step derived from registries and policy/trust checks (v2.0)."""

    step_id: str
    capability_id: str
    risk_level: RiskLevel
    params: dict[str, Any]
    description: str = ""
    envelope: Envelope | None = None


@dataclass(frozen=True)
class ValidatedPlan:
    """A validated plan safe for execution (v2.0)."""

    plan_description: str
    steps: list[ValidatedStep]
    metadata: dict[str, Any] = field(default_factory=dict)
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    errors: list[str] = field(default_factory=list)
