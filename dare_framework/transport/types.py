"""Transport domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Awaitable, Callable, ClassVar
from uuid import uuid4

from dare_framework.context.types import (
    AttachmentRef,
    MessageKind,
    MessageRole,
    _validate_message_components,
    _validate_message_payload_requirements,
)
class EnvelopeKind(StrEnum):
    """Strong envelope categories for transport dispatch."""

    MESSAGE = "message"
    SELECT = "select"
    ACTION = "action"
    CONTROL = "control"


class SelectKind(StrEnum):
    """Deterministic select lifecycle phases."""

    ASK = "ask"
    ANSWERED = "answered"


class SelectDomain(StrEnum):
    """Deterministic select interaction domains."""

    APPROVAL = "approval"
    CHOICE = "choice"
    FORM = "form"

@dataclass(frozen=True)
class EnvelopePayload:
    """Base typed payload carried by transport envelopes."""

    id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MessagePayload(EnvelopePayload):
    """Typed payload for message envelopes."""

    role: MessageRole = MessageRole.USER
    message_kind: MessageKind = MessageKind.CHAT
    text: str | None = None
    attachments: list[AttachmentRef] = field(default_factory=list)
    data: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _coerce_enum_member(self.role, MessageRole, "role"))
        object.__setattr__(self, "message_kind", _coerce_enum_member(self.message_kind, MessageKind, "message_kind"))
        object.__setattr__(self, "attachments", AttachmentRef.coerce_many(self.attachments))
        if self.data is not None and not isinstance(self.data, dict):
            raise TypeError(f"invalid data type: {type(self.data).__name__}")
        _validate_message_components(self.message_kind, self.attachments)
        _validate_message_payload_requirements(self.message_kind, self.data)


@dataclass(frozen=True)
class SelectPayload(EnvelopePayload):
    """Typed payload for select envelopes."""

    select_kind: SelectKind = SelectKind.ASK
    select_domain: SelectDomain = SelectDomain.CHOICE
    prompt: str | None = None
    options: list[dict[str, Any]] = field(default_factory=list)
    selected: Any = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "select_kind", _coerce_enum_member(self.select_kind, SelectKind, "select_kind"))
        object.__setattr__(self, "select_domain", _coerce_enum_member(self.select_domain, SelectDomain, "select_domain"))


@dataclass(frozen=True)
class ActionPayload(EnvelopePayload):
    """Typed payload for action envelopes."""

    resource_action: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    ok: bool | None = None
    result: Any = None
    code: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.resource_action, str):
            raise TypeError(
                f"invalid resource_action type: {type(self.resource_action).__name__}"
            )


@dataclass(frozen=True)
class ControlPayload(EnvelopePayload):
    """Typed payload for control envelopes."""

    control_id: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    ok: bool | None = None
    result: Any = None
    code: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.control_id, str):
            raise TypeError(f"invalid control_id type: {type(self.control_id).__name__}")
        normalized = self.control_id.strip()
        if not normalized:
            raise ValueError("control_id must not be empty")
        object.__setattr__(self, "control_id", normalized)


_PAYLOAD_TYPES_BY_KIND: dict[EnvelopeKind, tuple[type[Any], ...]] = {
    EnvelopeKind.MESSAGE: (MessagePayload,),
    EnvelopeKind.SELECT: (SelectPayload,),
    EnvelopeKind.ACTION: (ActionPayload,),
    EnvelopeKind.CONTROL: (ControlPayload,),
}


@dataclass(frozen=True)
class TransportEnvelope:
    """Transport envelope for agent/client messages."""

    id: str
    reply_to: str | None = None
    kind: EnvelopeKind = EnvelopeKind.MESSAGE
    payload: EnvelopePayload | None = None
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

        payload = self.payload
        expected_payload_types = _PAYLOAD_TYPES_BY_KIND.get(kind)
        if payload is not None and expected_payload_types is not None:
            if not isinstance(payload, expected_payload_types):
                expected_names = ", ".join(tp.__name__ for tp in expected_payload_types)
                raise TypeError(
                    "invalid payload type for envelope kind "
                    f"{kind.value!r}: expected {expected_names}, "
                    f"got {type(payload).__name__}"
                )


def new_envelope_id() -> str:
    """Generate a new envelope id."""

    return uuid4().hex


def _coerce_enum_member(raw: Any, enum_cls: type[StrEnum], field_name: str) -> StrEnum:
    """Normalize enum-backed payload fields from strings or enum members."""
    if isinstance(raw, enum_cls):
        return raw
    if not isinstance(raw, str):
        raise TypeError(f"invalid {field_name} type: {type(raw).__name__}")
    normalized = raw.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    try:
        return enum_cls(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}: {raw!r}") from exc


Sender = Callable[[TransportEnvelope], Awaitable[None]]
Receiver = Callable[[TransportEnvelope], Awaitable[None]]

__all__ = [
    "AttachmentRef",
    "EnvelopeKind",
    "EnvelopePayload",
    "MessageRole",
    "MessageKind",
    "MessagePayload",
    "SelectKind",
    "SelectDomain",
    "SelectPayload",
    "ActionPayload",
    "ControlPayload",
    "TransportEnvelope",
    "new_envelope_id",
    "Sender",
    "Receiver",
]
