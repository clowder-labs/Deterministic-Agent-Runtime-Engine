from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from dare_framework.contracts.evidence import Evidence
from dare_framework.contracts.risk import RiskLevel
from dare_framework.core.budget import Budget


@dataclass(frozen=True)
class EvidenceCondition:
    """A minimal, deterministic evidence predicate used by DonePredicate."""

    condition_type: str
    params: dict[str, Any] = field(default_factory=dict)

    def check(self, evidence: Iterable[Evidence]) -> bool:
        if self.condition_type == "always":
            return True
        if self.condition_type == "evidence_kind":
            kind = self.params.get("kind")
            return any(item.kind == kind for item in evidence)
        return False


@dataclass(frozen=True)
class DonePredicate:
    """Defines what 'done' means for a Tool Loop attempt (v2.0)."""

    required_keys: list[str] = field(default_factory=list)
    evidence_conditions: list[EvidenceCondition] = field(default_factory=list)
    require_all: bool = True
    description: str | None = None


@dataclass(frozen=True)
class Envelope:
    """Execution boundary for the Tool Loop (v2.0).

    Notes:
    - `allowed_capability_ids` is enforced by the Tool Loop. An empty list means "no explicit allow-list".
    - Budget enforcement is split between the envelope budget (per-loop) and the resource manager (global).
    """

    allowed_capability_ids: list[str] = field(default_factory=list)
    budget: Budget = field(default_factory=Budget)
    done_predicate: DonePredicate | None = None
    risk_level: RiskLevel = RiskLevel.READ_ONLY


@dataclass(frozen=True)
class ToolLoopRequest:
    """Tool Loop invocation payload (v2.1).

    `capability_id` and `params` are the *payload* for the current tool invocation.
    The `envelope` defines the execution boundary for the Tool Loop.

    Layering note:
    - `capability_id/params` MUST be treated as untrusted when they come from model output.
    - Security-critical fields (risk/approval) MUST be derived from trusted registries.
    """

    capability_id: str
    params: dict[str, Any] = field(default_factory=dict)
    envelope: Envelope = field(default_factory=Envelope)
