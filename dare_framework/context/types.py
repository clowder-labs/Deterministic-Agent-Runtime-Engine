"""context domain types (context-centric).

Alignment note:
- Context holds references (STM/LTM/Knowledge + Budget).
- Messages are assembled request-time via `Context.assemble(...)`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import TYPE_CHECKING, Any

from dare_framework.tool.types import CapabilityDescriptor

if TYPE_CHECKING:
    from dare_framework.model.types import Prompt


class MessageMark(str, Enum):
    """消息标记：IMMUTABLE 不可改，PERSISTENT 持久化（跨轮次保留），TEMPORARY 默认可清理。"""

    IMMUTABLE = "immutable"
    PERSISTENT = "persistent"
    TEMPORARY = "temporary"


class MessageRole(StrEnum):
    """Canonical framework message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageKind(StrEnum):
    """Canonical framework message semantic kinds."""

    CHAT = "chat"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SUMMARY = "summary"


class AttachmentKind(StrEnum):
    """Canonical attachment categories."""

    IMAGE = "image"


@dataclass
class AttachmentRef:
    """Typed attachment reference shared across transport/context/model."""

    kind: AttachmentKind = AttachmentKind.IMAGE
    uri: str = ""
    mime_type: str | None = None
    filename: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.kind = _coerce_enum_member(self.kind, AttachmentKind, "attachment kind")
        if not isinstance(self.uri, str) or not self.uri.strip():
            raise ValueError("attachment uri must not be empty")
        self.uri = self.uri.strip()
        self.mime_type = _coerce_optional_str(self.mime_type)
        self.filename = _coerce_optional_str(self.filename)
        self.metadata = dict(self.metadata or {})

    @classmethod
    def coerce(cls, raw: AttachmentRef | dict[str, Any]) -> AttachmentRef:
        """Normalize attachment input into AttachmentRef."""
        if isinstance(raw, cls):
            return raw
        if not isinstance(raw, dict):
            raise TypeError(f"invalid attachment ref type: {type(raw).__name__}")
        return cls(
            kind=raw.get("kind", AttachmentKind.IMAGE),
            uri=str(raw.get("uri") or ""),
            mime_type=_coerce_optional_str(raw.get("mime_type")),
            filename=_coerce_optional_str(raw.get("filename")),
            metadata=dict(raw.get("metadata") or {}) if isinstance(raw.get("metadata"), dict) else {},
        )

    @classmethod
    def coerce_many(cls, raw_items: list[AttachmentRef | dict[str, Any]] | None) -> list[AttachmentRef]:
        """Normalize a list of attachments into typed AttachmentRef objects."""
        if raw_items is None:
            return []
        return [cls.coerce(item) for item in raw_items]


@dataclass(init=False)
class Message:
    """Unified message format."""

    role: MessageRole
    kind: MessageKind
    text: str | None
    attachments: list[AttachmentRef]
    data: dict[str, Any] | None
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    mark: MessageMark = MessageMark.TEMPORARY
    id: str | None = None

    def __init__(
        self,
        role: MessageRole | str,
        text: str | None = None,
        *,
        kind: MessageKind | str = MessageKind.CHAT,
        attachments: list[AttachmentRef | dict[str, Any]] | None = None,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        mark: MessageMark | str = MessageMark.TEMPORARY,
        id: str | None = None,
    ) -> None:
        self.role = _coerce_enum_member(role, MessageRole, "message role")
        self.kind = _coerce_enum_member(kind, MessageKind, "message kind")
        self.text = text
        self.attachments = AttachmentRef.coerce_many(attachments)
        self.data = _coerce_optional_dict(data)
        _validate_message_components(self.kind, self.attachments)
        _validate_message_payload_requirements(self.kind, self.data)
        self.name = _coerce_optional_str(name)
        self.metadata = dict(metadata or {})
        self.mark = _coerce_enum_member(mark, MessageMark, "message mark")
        self.id = _coerce_optional_str(id)


@dataclass
class Budget:
    """Resource budget = limits + usage tracking."""

    # Limits
    max_tokens: int | None = None
    max_cost: float | None = None
    max_time_seconds: int | None = None
    max_tool_calls: int | None = None

    # Usage tracking
    used_tokens: float = 0.0
    used_cost: float = 0.0
    used_time_seconds: float = 0.0
    used_tool_calls: int = 0


@dataclass
class AssembledContext:
    """Request-time context for a single LLM call."""

    messages: list[Message]
    sys_prompt: Prompt | None = None
    tools: list[CapabilityDescriptor] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _coerce_enum_member(raw: Any, enum_cls: type[Enum], field_name: str):
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


def _coerce_optional_str(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _coerce_optional_dict(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError(f"invalid dict type: {type(raw).__name__}")
    return dict(raw)


def _validate_message_components(kind: MessageKind, attachments: list[AttachmentRef]) -> None:
    if attachments and kind in {MessageKind.THINKING, MessageKind.SUMMARY, MessageKind.TOOL_CALL}:
        raise ValueError(f"attachments are not supported for message kind {kind.value!r}")


def _validate_message_payload_requirements(kind: MessageKind, data: dict[str, Any] | None) -> None:
    if kind in {MessageKind.TOOL_CALL, MessageKind.TOOL_RESULT} and not data:
        raise ValueError(f"data is required for message kind {kind.value!r}")


__all__ = [
    "AssembledContext",
    "AttachmentKind",
    "AttachmentRef",
    "Budget",
    "Message",
    "MessageKind",
    "MessageMark",
    "MessageRole",
]
