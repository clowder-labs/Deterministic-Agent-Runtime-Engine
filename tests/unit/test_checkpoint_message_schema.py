from __future__ import annotations

from dare_framework.checkpoint.kernel import AgentState, AgentStateCheckpointManager
from dare_framework.context import AttachmentKind, AttachmentRef, Message, MessageKind, MessageMark, MessageRole


def test_checkpoint_serializes_and_restores_canonical_message_fields(tmp_path) -> None:
    manager = AgentStateCheckpointManager(backend="file", checkpoint_dir=tmp_path)
    state = AgentState(
        stm=[
            Message(
                role=MessageRole.USER,
                kind=MessageKind.CHAT,
                text="describe",
                attachments=[
                    AttachmentRef(
                        kind=AttachmentKind.IMAGE,
                        uri="https://example.com/a.png",
                        mime_type="image/png",
                    )
                ],
                data={"source": "camera"},
                name="alice",
                metadata={"trace": "1"},
                mark=MessageMark.PERSISTENT,
                id="msg-1",
            )
        ]
    )

    serialized = manager._serialize_state(state)
    restored = manager._deserialize_state(serialized)

    assert serialized["stm"][0]["role"] == MessageRole.USER.value
    assert serialized["stm"][0]["kind"] == MessageKind.CHAT.value
    assert serialized["stm"][0]["text"] == "describe"
    assert serialized["stm"][0]["attachments"][0]["kind"] == AttachmentKind.IMAGE.value

    restored_message = restored.stm[0]
    assert restored_message.role is MessageRole.USER
    assert restored_message.kind is MessageKind.CHAT
    assert restored_message.text == "describe"
    assert restored_message.attachments[0].uri == "https://example.com/a.png"
    assert restored_message.data == {"source": "camera"}
    assert restored_message.metadata == {"trace": "1"}
    assert restored_message.mark is MessageMark.PERSISTENT
    assert restored_message.id == "msg-1"
