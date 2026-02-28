"""Orchestration state management for the five-layer loop.

This module provides state holders used during five-layer loop execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from dare_framework.config.types import Config
from dare_framework.plan.types import Milestone, MilestoneSummary, SessionSummary, VerifyResult


@dataclass
class MilestoneState:
    """Internal milestone state holder used for plan isolation and verification."""

    milestone: Milestone
    attempts: int = 0
    reflections: list[str] = field(default_factory=list)
    attempted_plans: list[dict[str, Any]] = field(default_factory=list)
    evidence_collected: list[Any] = field(default_factory=list)

    def add_reflection(self, text: str) -> None:
        """Add a reflection note (e.g., from remediation)."""
        self.reflections.append(text)

    def add_attempt(self, attempt: dict[str, Any]) -> None:
        """Record a plan attempt (for debugging/audit)."""
        self.attempted_plans.append(attempt)

    def add_evidence(self, evidence: Any) -> None:
        """Collect evidence from tool execution."""
        self.evidence_collected.append(evidence)


@dataclass
class SessionContext:
    """Session-level context snapshot used for lifecycle management."""

    session_id: str
    task_id: str
    config: Config | None = None
    config_hash: str | None = None
    previous_session_summary: SessionSummary | None = None
    milestone_summaries: list[MilestoneSummary] = field(default_factory=list)
    started_at: float | None = None


@dataclass
class SessionState:
    """Session-level state holder."""

    task_id: str
    run_id: str = field(default_factory=lambda: uuid4().hex)
    milestone_states: list[MilestoneState] = field(default_factory=list)
    current_milestone_idx: int = 0
    session_context: SessionContext | None = None

    @property
    def current_milestone_state(self) -> MilestoneState | None:
        """Get the current milestone state, if any."""
        if 0 <= self.current_milestone_idx < len(self.milestone_states):
            return self.milestone_states[self.current_milestone_idx]
        return None


@dataclass
class MilestoneResult:
    """Result from a milestone loop execution."""

    success: bool
    outputs: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    verify_result: VerifyResult | None = None


__all__ = ["MilestoneResult", "MilestoneState", "SessionContext", "SessionState"]
