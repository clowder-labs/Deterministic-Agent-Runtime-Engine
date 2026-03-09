from __future__ import annotations

from types import SimpleNamespace

import pytest

from dare_framework.context.types import AttachmentKind, AttachmentRef, Message
from dare_framework.model.adapters.openai_adapter import OpenAIModelAdapter


def test_extract_usage_normalizes_reasoning_tokens() -> None:
    adapter = OpenAIModelAdapter()
    response = SimpleNamespace(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 11,
                "completion_tokens": 22,
                "total_tokens": 33,
                "completion_tokens_details": {
                    "reasoning_tokens": 9,
                },
            }
        },
        additional_kwargs={},
    )

    usage = adapter._extract_usage(response)

    assert usage == {
        "prompt_tokens": 11,
        "completion_tokens": 22,
        "total_tokens": 33,
        "reasoning_tokens": 9,
    }


def test_extract_usage_reads_reasoning_tokens_from_output_tokens_details() -> None:
    adapter = OpenAIModelAdapter()
    response = SimpleNamespace(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 3,
                "completion_tokens": 7,
                "total_tokens": 10,
                "output_tokens_details": {
                    "reasoning_tokens": 4,
                },
            }
        },
        additional_kwargs={},
    )

    usage = adapter._extract_usage(response)

    assert usage == {
        "prompt_tokens": 3,
        "completion_tokens": 7,
        "total_tokens": 10,
        "reasoning_tokens": 4,
    }


def test_extract_thinking_content_from_response_additional_kwargs() -> None:
    adapter = OpenAIModelAdapter()
    response = SimpleNamespace(
        additional_kwargs={
            "reasoning_content": "internal reasoning",
        },
        response_metadata={},
    )

    assert adapter._extract_thinking_content(response) == "internal reasoning"


def test_to_langchain_messages_supports_chat_text_with_multiple_images(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = OpenAIModelAdapter()
    import dare_framework.model.adapters.openai_adapter as module

    monkeypatch.setattr(module, "SystemMessage", lambda content: {"role": "system", "content": content})
    monkeypatch.setattr(module, "HumanMessage", lambda content: {"role": "user", "content": content})
    monkeypatch.setattr(module, "AIMessage", lambda content, tool_calls=None: {"role": "assistant", "content": content, "tool_calls": tool_calls or []})
    monkeypatch.setattr(module, "ToolMessage", lambda content, tool_call_id: {"role": "tool", "content": content, "tool_call_id": tool_call_id})

    mapped = adapter._to_langchain_messages(
        [
            Message(
                role="user",
                text="describe both",
                attachments=[
                    AttachmentRef(kind=AttachmentKind.IMAGE, uri="https://example.com/a.png"),
                    AttachmentRef(kind=AttachmentKind.IMAGE, uri="https://example.com/b.png"),
                ],
            )
        ]
    )

    assert mapped == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe both"},
                {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
                {"type": "image_url", "image_url": {"url": "https://example.com/b.png"}},
            ],
        }
    ]


def test_to_langchain_messages_prefers_structured_tool_data(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = OpenAIModelAdapter()
    import dare_framework.model.adapters.openai_adapter as module

    monkeypatch.setattr(module, "SystemMessage", lambda content: {"role": "system", "content": content})
    monkeypatch.setattr(module, "HumanMessage", lambda content: {"role": "user", "content": content})
    monkeypatch.setattr(module, "AIMessage", lambda content, tool_calls=None: {"role": "assistant", "content": content, "tool_calls": tool_calls or []})
    monkeypatch.setattr(module, "ToolMessage", lambda content, tool_call_id: {"role": "tool", "content": content, "tool_call_id": tool_call_id})

    mapped = adapter._to_langchain_messages(
        [
            Message(
                role="assistant",
                kind="tool_call",
                text="call tool",
                data={
                    "tool_calls": [
                        {"id": "call_1", "name": "search", "arguments": {"q": "docs"}},
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
    )

    assert mapped[0]["tool_calls"] == [{"id": "call_1", "name": "search", "args": {"q": "docs"}}]
    assert mapped[1]["tool_call_id"] == "call_1"


def test_tool_call_messages_require_data_instead_of_metadata_fallback() -> None:
    with pytest.raises(ValueError, match="data is required"):
        Message(
            role="assistant",
            kind="tool_call",
            text="legacy metadata only",
            metadata={"tool_calls": [{"id": "call_1", "name": "search", "arguments": {"q": "docs"}}]},
        )


def test_serialize_langchain_content_rejects_unsupported_attachment_kind() -> None:
    adapter = OpenAIModelAdapter()
    fake_message = SimpleNamespace(
        text="bad attachment",
        attachments=[SimpleNamespace(kind="file", uri="https://example.com/file.txt")],
    )

    with pytest.raises(ValueError, match="unsupported attachment kind"):
        adapter._serialize_langchain_content(fake_message)
