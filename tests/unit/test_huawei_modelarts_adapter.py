from __future__ import annotations

from types import SimpleNamespace

import pytest

from dare_framework.context.types import AttachmentKind, AttachmentRef, Message
from dare_framework.model.adapters.huawei_modelarts_adapter import (
    HuaweiModelArtsModelAdapter,
    _extract_reasoning_tokens,
    _extract_thinking_content,
    _serialize_messages,
)


def test_adapter_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API key is required"):
        HuaweiModelArtsModelAdapter(api_key=None, model="modelarts-pro")


def test_adapter_requires_model() -> None:
    with pytest.raises(ValueError, match="model is required"):
        HuaweiModelArtsModelAdapter(api_key="dummy", model=None)


def test_serialize_messages_preserves_assistant_tool_calls() -> None:
    messages = [
        Message(role="user", text="Need a filename"),
        Message(
            role="assistant",
            text="I need your confirmation first.",
            data={
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "ask_user",
                        "arguments": {
                            "questions": [
                                {
                                    "header": "Target",
                                    "question": "Pick a file name",
                                    "options": [
                                        {"label": "a.txt", "description": "A"},
                                        {"label": "b.txt", "description": "B"},
                                    ],
                                }
                            ]
                        },
                    }
                ]
            },
        ),
        Message(
            role="tool",
            name="call_1",
            text='{"success": true, "output": {"answers": {"Pick a file name": "a.txt"}}}',
        ),
    ]

    serialized = _serialize_messages(messages)

    assistant_payload = serialized[1]
    assert "tool_calls" in assistant_payload
    tool_call = assistant_payload["tool_calls"][0]
    assert tool_call["id"] == "call_1"
    assert tool_call["type"] == "function"
    assert tool_call["function"]["name"] == "ask_user"
    assert isinstance(tool_call["function"]["arguments"], str)
    assert serialized[2]["tool_call_id"] == "call_1"


def test_serialize_messages_supports_chat_text_with_image_attachments() -> None:
    messages = [
        Message(
            role="user",
            text="describe both",
            attachments=[
                AttachmentRef(kind=AttachmentKind.IMAGE, uri="https://example.com/a.png"),
                AttachmentRef(kind=AttachmentKind.IMAGE, uri="https://example.com/b.png"),
            ],
        )
    ]

    serialized = _serialize_messages(messages)

    assert serialized == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe both"},
                {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
                {"type": "image_url", "image_url": {"url": "https://example.com/b.png"}},
            ],
        }
    ]


def test_serialize_messages_prefers_structured_data_for_tool_history() -> None:
    messages = [
        Message(
            role="assistant",
            text="call tool",
            kind="tool_call",
            data={
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "search",
                        "arguments": {"q": "docs"},
                    }
                ]
            },
        ),
        Message(
            role="tool",
            kind="tool_result",
            text="done",
            data={"tool_call_id": "call_1"},
        ),
    ]

    serialized = _serialize_messages(messages)

    assert serialized[0]["tool_calls"][0]["id"] == "call_1"
    assert serialized[1]["tool_call_id"] == "call_1"


def test_extract_thinking_content_from_message_fields() -> None:
    message = SimpleNamespace(reasoning="step by step", reasoning_content=None, additional_kwargs={})
    assert _extract_thinking_content(message) == "step by step"


def test_extract_reasoning_tokens_from_completion_tokens_details() -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=1,
            completion_tokens=2,
            total_tokens=3,
            reasoning_tokens=None,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=7),
        )
    )
    assert _extract_reasoning_tokens(response) == 7
