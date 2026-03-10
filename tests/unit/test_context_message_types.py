from __future__ import annotations

import pytest

from dare_framework.context import AttachmentKind, AttachmentRef, Message, MessageKind, MessageMark, MessageRole


def test_message_normalizes_role_kind_and_attachment_refs() -> None:
    message = Message(
        role="user",
        kind="chat",
        text="look at these",
        attachments=[
            {
                "kind": "image",
                "uri": "https://example.com/a.png",
                "mime_type": "image/png",
                "filename": "a.png",
            }
        ],
        mark=MessageMark.PERSISTENT,
        id="msg-1",
    )

    assert message.role is MessageRole.USER
    assert message.kind is MessageKind.CHAT
    assert message.text == "look at these"
    assert len(message.attachments) == 1
    assert isinstance(message.attachments[0], AttachmentRef)
    assert message.attachments[0].kind is AttachmentKind.IMAGE
    assert message.attachments[0].uri == "https://example.com/a.png"
    assert message.mark is MessageMark.PERSISTENT
    assert message.id == "msg-1"

def test_message_accepts_text_as_canonical_content_field() -> None:
    message = Message(role=MessageRole.ASSISTANT, text="done")

    assert message.role is MessageRole.ASSISTANT
    assert message.kind is MessageKind.CHAT
    assert message.text == "done"


def test_attachment_ref_rejects_invalid_kind() -> None:
    with pytest.raises(ValueError, match="invalid attachment kind"):
        AttachmentRef(kind="video", uri="https://example.com/v.mp4")  # type: ignore[arg-type]

def test_message_rejects_non_dict_data() -> None:
    with pytest.raises(TypeError, match="invalid dict type"):
        Message(role="user", text="a", data="b")  # type: ignore[arg-type]


def test_message_rejects_attachments_for_thinking_kind() -> None:
    with pytest.raises(ValueError, match="attachments are not supported"):
        Message(
            role="assistant",
            kind="thinking",
            text="internal reasoning",
            attachments=[{"kind": "image", "uri": "https://example.com/a.png"}],
        )


def test_message_requires_structured_data_for_tool_call_kind() -> None:
    with pytest.raises(ValueError, match="data is required"):
        Message(
            role="assistant",
            kind="tool_call",
            text="call search_docs",
        )


def test_message_requires_structured_data_for_tool_result_kind() -> None:
    with pytest.raises(ValueError, match="data is required"):
        Message(
            role="tool",
            kind="tool_result",
            text="done",
        )
