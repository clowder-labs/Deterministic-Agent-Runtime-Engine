"""Kernel event log models (v2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import uuid4


@dataclass(frozen=True)
class Event:
    """Append-only event record used for audit and replay (WORM)."""

    event_type: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    prev_hash: str | None = None
    event_hash: str | None = None


@dataclass(frozen=True)
class RuntimeSnapshot:
    """A minimal replay snapshot produced from the event log.

    v2.0 leaves replay semantics open; the initial implementation may return an event window
    and correlation metadata needed for debugging and verification.
    """

    from_event_id: str
    events: Sequence[Event]

