from __future__ import annotations

import pytest

from dare_framework.context.types import AttachmentKind, Message, MessageKind
from dare_framework.knowledge import KnowledgeConfig, create_knowledge
from dare_framework.knowledge._internal.vector_knowledge.document import Document
from dare_framework.memory import LongTermMemoryConfig, create_long_term_memory


def test_create_long_term_memory_returns_none_for_empty_or_vector_without_embedding() -> None:
    assert create_long_term_memory({}) is None
    assert (
        create_long_term_memory({"type": "vector", "storage": "in_memory"}, embedding_adapter=None)
        is None
    )


@pytest.mark.asyncio
async def test_rawdata_long_term_memory_roundtrip_and_defaults() -> None:
    ltm = create_long_term_memory(
        LongTermMemoryConfig(type="rawdata", storage="in_memory"),
    )
    assert ltm is not None

    await ltm.persist(
        [
            Message(
                role="assistant",
                kind=MessageKind.CHAT,
                name="memo",
                text="alpha memory",
                attachments=[
                    {
                        "kind": AttachmentKind.IMAGE,
                        "uri": "https://example.com/alpha.png",
                        "mime_type": "image/png",
                    }
                ],
                data={"source": "memory"},
                metadata={"topic": "alpha"},
            ),
            Message(role="user", kind=MessageKind.CHAT, text="", metadata={"topic": "blank"}),
        ]
    )

    alpha_matches = ltm.get("alpha", top_k=5)
    assert len(alpha_matches) == 1
    assert alpha_matches[0].role == "assistant"
    assert alpha_matches[0].kind == MessageKind.CHAT
    assert alpha_matches[0].name == "memo"
    assert alpha_matches[0].metadata["topic"] == "alpha"
    assert alpha_matches[0].data == {"source": "memory"}
    assert len(alpha_matches[0].attachments) == 1
    assert alpha_matches[0].attachments[0].kind == AttachmentKind.IMAGE
    assert alpha_matches[0].attachments[0].uri == "https://example.com/alpha.png"

    # Non-int top_k should fallback to default without raising.
    all_matches = ltm.get("", top_k="invalid")  # type: ignore[arg-type]
    assert len(all_matches) >= 2
    blank = next(msg for msg in all_matches if msg.metadata.get("topic") == "blank")
    assert blank.text == ""


def test_create_knowledge_returns_none_for_empty_or_vector_without_embedding() -> None:
    assert create_knowledge({}) is None
    assert create_knowledge(KnowledgeConfig(type="vector", storage="in_memory"), embedding_adapter=None) is None


def test_rawdata_knowledge_direct_add_get_remove_and_clear() -> None:
    knowledge = create_knowledge(
        KnowledgeConfig(type="rawdata", storage="in_memory"),
    )
    assert knowledge is not None

    knowledge.add("python basics", metadata={"source": "doc-a", "tag": "lang"})
    knowledge.add("rust ownership", metadata={"source": "doc-b"})

    matches = knowledge.get("python", top_k=5)
    assert len(matches) == 1
    first = matches[0]
    assert first.text == "python basics"
    assert first.name == "doc-a"
    assert first.metadata["tag"] == "lang"
    assert "document_id" in first.metadata

    record_id = first.metadata["document_id"]
    assert knowledge.remove(record_id) is True  # type: ignore[attr-defined]
    assert knowledge.record_count == 1  # type: ignore[attr-defined]

    knowledge.clear()  # type: ignore[attr-defined]
    assert knowledge.record_count == 0  # type: ignore[attr-defined]


def test_vector_document_to_message_uses_canonical_text_field() -> None:
    document = Document(
        content="vector memory",
        metadata={"source": "doc-a"},
    )

    message = document.to_message(role="assistant")

    assert message.text == "vector memory"
    assert message.name == "doc-a"
    assert message.metadata["document_id"] == document.id


def test_config_from_dict_falls_back_to_supported_memory_and_knowledge_modes() -> None:
    ltm_cfg = LongTermMemoryConfig.from_dict({"type": "unsupported", "storage": "unsupported"})
    assert ltm_cfg.type == "rawdata"
    assert ltm_cfg.storage == "in_memory"

    knowledge_cfg = KnowledgeConfig.from_dict({"type": "unsupported", "storage": "unsupported"})
    assert knowledge_cfg.type == "vector"
    assert knowledge_cfg.storage == "in_memory"
