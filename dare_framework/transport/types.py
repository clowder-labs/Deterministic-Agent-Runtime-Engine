"""Transport domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable
from uuid import uuid4


class EnvelopeKind(StrEnum):
    """Strong envelope categories for transport dispatch."""

    MESSAGE = "message"
    ACTION = "action"
    CONTROL = "control"


@dataclass(frozen=True)
class TransportEnvelope:
    """Transport envelope for agent/client messages."""

    id: str
    reply_to: str | None = None
    kind: EnvelopeKind = EnvelopeKind.MESSAGE
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
            return
        if not isinstance(kind, EnvelopeKind):
            raise TypeError(f"invalid envelope kind type: {type(kind).__name__}")


def new_envelope_id() -> str:
    """Generate a new envelope id."""

    return uuid4().hex


Sender = Callable[[TransportEnvelope], Awaitable[None]]
Receiver = Callable[[TransportEnvelope], Awaitable[None]]

__all__ = [
    "EnvelopeKind",
    "TransportEnvelope",
    "new_envelope_id",
    "Sender",
    "Receiver",
]
