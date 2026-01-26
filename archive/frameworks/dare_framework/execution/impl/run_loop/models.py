"""Kernel run loop models (v2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RunLoopState(Enum):
    """Tick-based run loop states (v2.0)."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    PAUSED = "paused"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass(frozen=True)
class TickResult:
    """Result of a single scheduling tick (debug/visualization friendly)."""

    state: RunLoopState
    produced_event_ids: list[str] = field(default_factory=list)
    completed: bool = False

