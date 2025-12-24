from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import time


EventID = str


@dataclass
class EventFilter:
    event_types: list[str] | None = None
    milestone_id: str | None = None
    since_timestamp: float | None = None
    until_timestamp: float | None = None


@dataclass
class Event:
    event_type: str = ""
    timestamp: float = field(default_factory=time.time)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionStartedEvent(Event):
    user_input: str = ""
    has_previous_context: bool = False

    def __post_init__(self) -> None:
        self.event_type = "session_started"
        self.payload = {
            "user_input": self.user_input,
            "has_previous_context": self.has_previous_context,
        }


@dataclass
class PlanValidationFailedEvent(Event):
    milestone_id: str = ""
    attempt: int = 0
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.event_type = "plan_validation_failed"
        self.payload = {
            "milestone_id": self.milestone_id,
            "attempt": self.attempt,
            "errors": self.errors,
        }


@dataclass
class RemediateEvent(Event):
    milestone_id: str = ""
    attempt: int = 0
    failure_reason: str | None = None
    reflection: str = ""

    def __post_init__(self) -> None:
        self.event_type = "remediate"
        self.payload = {
            "milestone_id": self.milestone_id,
            "attempt": self.attempt,
            "failure_reason": self.failure_reason,
            "reflection": self.reflection,
        }
