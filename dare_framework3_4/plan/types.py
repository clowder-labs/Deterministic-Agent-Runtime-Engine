"""Plan domain types (minimal) for v4.0 tool boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dare_framework3_4.context.context import Budget
from dare_framework3_4.security.types import RiskLevel


@dataclass(frozen=True)
class DonePredicate:
    """Predicate for determining tool loop completion."""

    required_keys: list[str] = field(default_factory=list)
    evidence_conditions: list[dict[str, Any]] = field(default_factory=list)
    require_all: bool = True
    description: str | None = None


def _default_budget() -> Budget:
    return Budget()


def _default_risk_level() -> RiskLevel:
    return RiskLevel.READ_ONLY


@dataclass(frozen=True)
class Envelope:
    """Execution boundary for the Tool Loop."""

    allowed_capability_ids: list[str] = field(default_factory=list)
    budget: Budget = field(default_factory=_default_budget)
    done_predicate: DonePredicate | None = None
    risk_level: RiskLevel = field(default_factory=_default_risk_level)


__all__ = ["DonePredicate", "Envelope"]
