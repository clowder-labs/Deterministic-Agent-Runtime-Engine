"""Canonical input normalization helpers for agent entry points."""

from __future__ import annotations

from dare_framework.context import Message
from dare_framework.context.types import MessageKind, MessageRole
from dare_framework.plan.types import Task


def coerce_user_message(value: str | Message) -> Message:
    """Normalize top-level agent input into a canonical user-facing Message."""
    if isinstance(value, Message):
        if value.role is not MessageRole.USER:
            raise ValueError("agent input message role must be 'user'")
        if value.kind is not MessageKind.CHAT:
            raise ValueError("agent input message kind must be 'chat'")
        return value
    if not isinstance(value, str):
        raise TypeError(f"unsupported agent input type: {type(value).__name__}")
    return Message(role=MessageRole.USER, kind=MessageKind.CHAT, text=value)


def build_task_from_message(message: Message) -> Task:
    """Project a canonical user message into the internal orchestration Task shape."""
    metadata = dict(message.metadata)
    raw_task_id = metadata.get("task_id")
    task_id = raw_task_id.strip() if isinstance(raw_task_id, str) and raw_task_id.strip() else None
    return Task(
        description=message.text or "",
        task_id=task_id,
        metadata=metadata,
        input_message=message,
    )


def preview_text(value: str | Message) -> str:
    """Return a stable human-readable text preview for logs and envelopes."""
    if isinstance(value, Message):
        return value.text or ""
    if not isinstance(value, str):
        raise TypeError(f"unsupported agent input type: {type(value).__name__}")
    return value


__all__ = [
    "build_task_from_message",
    "coerce_user_message",
    "preview_text",
]
