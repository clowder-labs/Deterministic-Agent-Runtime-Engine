from __future__ import annotations

import pytest

from dare_framework.agent._internal.input_normalizer import build_task_from_message, coerce_user_message
from dare_framework.context import Message
from dare_framework.plan.types import Task


def test_build_task_from_message_uses_metadata_task_id() -> None:
    message = Message(
        role="user",
        text="hello",
        metadata={"task_id": "task-123", "conversation_id": "conv-1"},
    )

    task = build_task_from_message(message)

    assert task.task_id == "task-123"
    assert task.description == "hello"
    assert task.input_message is message
    assert task.metadata["conversation_id"] == "conv-1"


def test_coerce_user_message_rejects_task_input() -> None:
    with pytest.raises(TypeError, match="unsupported agent input type: Task"):
        coerce_user_message(Task(description="legacy"))


def test_coerce_user_message_rejects_non_user_role_message() -> None:
    with pytest.raises(ValueError, match="agent input message role must be 'user'"):
        coerce_user_message(Message(role="assistant", text="hello"))


def test_coerce_user_message_rejects_non_chat_kind_message() -> None:
    with pytest.raises(ValueError, match="agent input message kind must be 'chat'"):
        coerce_user_message(Message(role="user", kind="tool_result", text=None, data={"ok": True}))
