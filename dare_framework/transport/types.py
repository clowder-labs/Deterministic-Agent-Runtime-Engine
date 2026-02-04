"""Transport domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal
from uuid import uuid4

EnvelopeKind = Literal["data", "control"]


@dataclass(frozen=True)
class TransportEnvelope:
    """Transport envelope for agent/client messages."""

    id: str
    reply_to: str | None = None
    kind: EnvelopeKind = "data"
    type: str = "message"
    payload: Any = None
    meta: dict[str, Any] = field(default_factory=dict)
    stream_id: str | None = None
    seq: int | None = None


def new_envelope_id() -> str:
    """Generate a new envelope id."""

    return uuid4().hex


Sender = Callable[[TransportEnvelope], Awaitable[None]]
Receiver = Callable[[TransportEnvelope], Awaitable[None]]
EnvelopeEncoder = Callable[[TransportEnvelope], TransportEnvelope]
EnvelopeDecoder = Callable[[TransportEnvelope], TransportEnvelope]

__all__ = [
    "EnvelopeKind",
    "TransportEnvelope",
    "new_envelope_id",
    "Sender",
    "Receiver",
    "EnvelopeEncoder",
    "EnvelopeDecoder",
]
