"""event domain types (audit/replay)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import uuid4


@dataclass(frozen=True)
class Event:
    """Append-only event record used for audit and replay."""

    event_type: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    prev_hash: str | None = None
    event_hash: str | None = None


@dataclass(frozen=True)
class RuntimeSnapshot:
    """A minimal replay snapshot produced from the event log."""

    from_event_id: str
    events: Sequence[Event]


__all__ = ["Event", "RuntimeSnapshot"]
