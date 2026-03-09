from __future__ import annotations

from types import SimpleNamespace

import pytest

from dare_framework.context.types import AttachmentKind, AttachmentRef, Message
from dare_framework.model.adapters.anthropic_adapter import (
    AnthropicModelAdapter,
    _extract_response_text,
    _extract_thinking_content,
    _extract_tool_calls,
    _extract_usage,
    _resolve_model_name,
    _serialize_system_and_messages,
)
from dare_framework.model.types import GenerateOptions, ModelInput
from dare_framework.tool.types import CapabilityDescriptor, CapabilityType


def test_resolve_model_name_prefers_explicit_model_value() -> None:
    assert _resolve_model_name(model="claude-sonnet-4-5", env_model="claude-opus-4-1") == "claude-sonnet-4-5"


def test_resolve_model_name_uses_env_model_when_explicit_missing() -> None:
    assert _resolve_model_name(model=None, env_model="claude-opus-4-1") == "claude-opus-4-1"


def test_resolve_model_name_requires_model_source() -> None:
    with pytest.raises(ValueError, match="Anthropic model is required"):
        _resolve_model_name(model=None, env_model=None)


def test_serialize_system_and_messages_preserves_tool_history() -> None:
    system_prompt, payload_messages = _serialize_system_and_messages(
        [
            Message(role="system", text="You are a helpful assistant."),
            Message(role="user", text="Need a filename"),
            Message(
                role="assistant",
                text="I need your confirmation first.",
                data={
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "name": "ask_user",
                            "arguments": {"question": "Pick a file name"},
                        }
                    ]
                },
            ),
            Message(
                role="tool",
                name="call_1",
                text="a.txt",
            ),
        ]
    )

    assert system_prompt == "You are a helpful assistant."
    assert payload_messages[0] == {"role": "user", "content": "Need a filename"}
    assert payload_messages[1]["role"] == "assistant"
    assert payload_messages[1]["content"][0]["type"] == "text"
    assert payload_messages[1]["content"][1] == {
        "type": "tool_use",
        "id": "call_1",
        "name": "ask_user",
        "input": {"question": "Pick a file name"},
    }
    assert payload_messages[2] == {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": "a.txt"}],
    }


def test_serialize_system_and_messages_supports_chat_text_with_image_attachments() -> None:
    system_prompt, payload_messages = _serialize_system_and_messages(
        [
            Message(
                role="user",
                text="describe image",
                attachments=[
                    AttachmentRef(
                        kind=AttachmentKind.IMAGE,
                        uri="https://example.com/a.png",
                        mime_type="image/png",
                    ),
                    AttachmentRef(
                        kind=AttachmentKind.IMAGE,
                        uri="https://example.com/b.png",
                        mime_type="image/png",
                    ),
                ],
            )
        ]
    )

    assert system_prompt is None
    assert payload_messages == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe image"},
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": "https://example.com/a.png",
                    },
                },
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": "https://example.com/b.png",
                    },
                },
            ],
        }
    ]


def test_serialize_system_and_messages_supports_inline_data_uri_images() -> None:
    system_prompt, payload_messages = _serialize_system_and_messages(
        [
            Message(
                role="user",
                text="describe inline image",
                attachments=[
                    AttachmentRef(
                        kind=AttachmentKind.IMAGE,
                        uri="data:image/png;base64,cG5nZGF0YQ==",
                        mime_type="image/png",
                    )
                ],
            )
        ]
    )

    assert system_prompt is None
    assert payload_messages == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe inline image"},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": "cG5nZGF0YQ==",
                    },
                },
            ],
        }
    ]


def test_tool_call_messages_require_data_instead_of_metadata_fallback() -> None:
    with pytest.raises(ValueError, match="data is required"):
        Message(
            role="assistant",
            kind="tool_call",
            text="legacy metadata only",
            metadata={"tool_calls": [{"id": "call_1", "name": "search", "arguments": {"q": "docs"}}]},
        )


def test_extract_response_fields_from_content_blocks() -> None:
    blocks = [
        SimpleNamespace(type="thinking", thinking="internal reasoning"),
        SimpleNamespace(type="text", text="final answer"),
        SimpleNamespace(type="tool_use", id="toolu_1", name="search", input={"q": "hi"}),
    ]
    usage = SimpleNamespace(
        input_tokens=12,
        output_tokens=8,
        output_tokens_details=SimpleNamespace(reasoning_tokens=3),
    )

    assert _extract_response_text(blocks) == "final answer"
    assert _extract_thinking_content(blocks) == "internal reasoning"
    assert _extract_tool_calls(blocks) == [{"id": "toolu_1", "name": "search", "arguments": {"q": "hi"}}]
    assert _extract_usage(usage) == {
        "prompt_tokens": 12,
        "completion_tokens": 8,
        "total_tokens": 20,
        "reasoning_tokens": 3,
    }


@pytest.mark.asyncio
async def test_generate_builds_anthropic_payload_and_parses_response() -> None:
    calls: list[dict[str, object]] = []

    class _MessagesAPI:
        async def create(self, **kwargs):  # noqa: ANN003
            calls.append(kwargs)
            return SimpleNamespace(
                content=[
                    SimpleNamespace(type="thinking", thinking="plan"),
                    SimpleNamespace(type="tool_use", id="toolu_1", name="search", input={"q": "docs"}),
                    SimpleNamespace(type="text", text="done"),
                ],
                usage=SimpleNamespace(input_tokens=7, output_tokens=5),
                stop_reason="end_turn",
            )

    class _FakeClient:
        def __init__(self) -> None:
            self.messages = _MessagesAPI()

    adapter = AnthropicModelAdapter(api_key="test-key", model="claude-opus-4-1")
    adapter._client = _FakeClient()  # type: ignore[assignment]

    result = await adapter.generate(
        ModelInput(
            messages=[Message(role="system", text="You are careful."), Message(role="user", text="hello")],
            tools=[
                CapabilityDescriptor(
                    id="search-docs",
                    type=CapabilityType.TOOL,
                    name="search",
                    description="Search docs",
                    input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
                    output_schema={"type": "object"},
                    metadata={},
                )
            ],
        ),
        options=GenerateOptions(max_tokens=128, stop=["STOP"]),
    )

    assert calls
    params = calls[0]
    assert params["model"] == "claude-opus-4-1"
    assert params["system"] == "You are careful."
    assert params["stop_sequences"] == ["STOP"]
    assert params["max_tokens"] == 128
    assert params["tools"] == [
        {
            "name": "search",
            "description": "Search docs",
            "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}},
        }
    ]

    assert result.content == "done"
    assert result.thinking_content == "plan"
    assert result.tool_calls == [{"id": "toolu_1", "name": "search", "arguments": {"q": "docs"}}]
    assert result.usage == {"prompt_tokens": 7, "completion_tokens": 5, "total_tokens": 12}


@pytest.mark.asyncio
async def test_generate_keeps_normalized_max_tokens_when_extra_value_is_none() -> None:
    calls: list[dict[str, object]] = []

    class _MessagesAPI:
        async def create(self, **kwargs):  # noqa: ANN003
            calls.append(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="ok")], usage=None, stop_reason="end_turn")

    class _FakeClient:
        def __init__(self) -> None:
            self.messages = _MessagesAPI()

    adapter = AnthropicModelAdapter(api_key="test-key", model="claude-sonnet-4-5", extra={"max_tokens": None})
    adapter._client = _FakeClient()  # type: ignore[assignment]

    await adapter.generate(ModelInput(messages=[Message(role="user", text="hello")]))

    assert calls
    assert calls[0]["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_generate_normalizes_string_max_tokens_from_extra() -> None:
    calls: list[dict[str, object]] = []

    class _MessagesAPI:
        async def create(self, **kwargs):  # noqa: ANN003
            calls.append(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="ok")], usage=None, stop_reason="end_turn")

    class _FakeClient:
        def __init__(self) -> None:
            self.messages = _MessagesAPI()

    adapter = AnthropicModelAdapter(api_key="test-key", model="claude-opus-4-1", extra={"max_tokens": "256"})
    adapter._client = _FakeClient()  # type: ignore[assignment]

    await adapter.generate(ModelInput(messages=[Message(role="user", text="hello")]))

    assert calls
    assert calls[0]["max_tokens"] == 256
