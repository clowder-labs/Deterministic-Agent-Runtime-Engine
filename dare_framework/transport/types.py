"""Transport domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable
from uuid import uuid4


class EnvelopeKind(StrEnum):
    """Strong envelope categories for transport dispatch."""

    MESSAGE = "message"
    SELECT = "select"
    ACTION = "action"
    CONTROL = "control"


class TransportEventType(StrEnum):
    """Canonical event categories carried by message envelopes."""

    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    ERROR = "error"
    STATUS = "status"

    # Legacy aliases kept for backward compatibility with existing emitters/consumers.
    RESULT = "result"
    HOOK = "hook"
    APPROVAL_PENDING = "approval.pending"
    APPROVAL_RESOLVED = "approval.resolved"


_LEGACY_PAYLOAD_EVENT_TYPE_MAP: dict[str, str] = {
    # Only legacy aliases that differ from canonical event_type values.
    "approval_pending": TransportEventType.APPROVAL_PENDING.value,
    "approval_resolved": TransportEventType.APPROVAL_RESOLVED.value,
    "tool.result": TransportEventType.TOOL_RESULT.value,
    "tool.call": TransportEventType.TOOL_CALL.value,
}

_LEGACY_TO_CANONICAL_EVENT_TYPE_MAP: dict[str, str] = {
    TransportEventType.RESULT.value: TransportEventType.MESSAGE.value,
    TransportEventType.HOOK.value: TransportEventType.STATUS.value,
    TransportEventType.APPROVAL_PENDING.value: TransportEventType.STATUS.value,
    TransportEventType.APPROVAL_RESOLVED.value: TransportEventType.STATUS.value,
}


def normalize_transport_event_type(raw: str | None) -> str | None:
    """Normalize legacy/new event_type strings into canonical values."""
    if raw is None:
        return None
    normalized = raw.strip()
    if not normalized:
        return None
    return _LEGACY_PAYLOAD_EVENT_TYPE_MAP.get(normalized, normalized)


def canonicalize_transport_event_type(raw: str | None) -> str | None:
    """Canonicalize legacy event aliases into the stable transport taxonomy."""
    normalized = normalize_transport_event_type(raw)
    if normalized is None:
        return None
    return _LEGACY_TO_CANONICAL_EVENT_TYPE_MAP.get(normalized, normalized)


@dataclass(frozen=True)
class TransportEnvelope:
    """Transport envelope for agent/client messages."""

    id: str
    reply_to: str | None = None
    kind: EnvelopeKind = EnvelopeKind.MESSAGE
    event_type: str | None = None
    payload: Any = None
    meta: dict[str, Any] = field(default_factory=dict)
    stream_id: str | None = None
    seq: int | None = None

    def __post_init__(self) -> None:
        kind = self.kind
        if isinstance(kind, str):
            try:
                object.__setattr__(self, "kind", EnvelopeKind(kind))
            except ValueError as exc:
                raise ValueError(f"invalid envelope kind: {kind!r}") from exc
            kind = self.kind
        if not isinstance(kind, EnvelopeKind):
            raise TypeError(f"invalid envelope kind type: {type(kind).__name__}")

        event_type = self.event_type
        if isinstance(event_type, TransportEventType):
            object.__setattr__(self, "event_type", event_type.value)
            return
        if event_type is None:
            return
        if not isinstance(event_type, str):
            raise TypeError(f"invalid event_type type: {type(event_type).__name__}")
        normalized = normalize_transport_event_type(event_type)
        if normalized is None:
            raise ValueError("event_type must not be empty")
        object.__setattr__(self, "event_type", normalized)


def new_envelope_id() -> str:
    """Generate a new envelope id."""

    return uuid4().hex


Sender = Callable[[TransportEnvelope], Awaitable[None]]
Receiver = Callable[[TransportEnvelope], Awaitable[None]]

__all__ = [
    "EnvelopeKind",
    "TransportEventType",
    "normalize_transport_event_type",
    "canonicalize_transport_event_type",
    "TransportEnvelope",
    "new_envelope_id",
    "Sender",
    "Receiver",
]
