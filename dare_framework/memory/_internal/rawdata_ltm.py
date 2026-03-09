"""Long-term memory implementation backed by raw data storage (IRawDataStore)."""

from __future__ import annotations

from typing import Any, Literal

from dare_framework.context import AttachmentRef, Message, MessageKind, MessageMark, MessageRole
from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.memory.kernel import ILongTermMemory
from dare_framework.knowledge._internal.rawdata_knowledge.storage.interfaces import (
    IRawDataStore,
)


def _message_to_content_metadata(message: Message) -> tuple[str, dict[str, Any]]:
    """Serialize Message to (content, metadata) for storage.

    Raw-data storage requires a non-empty searchable text payload. Canonical message
    fields are persisted in metadata so text-less rich messages can still be restored
    losslessly.
    """
    content = message.text if message.text else " "
    metadata: dict[str, Any] = {
        "role": message.role.value,
        "kind": message.kind.value,
        "text": message.text,
        "attachments": [
            {
                "kind": attachment.kind.value,
                "uri": attachment.uri,
                "mime_type": attachment.mime_type,
                "filename": attachment.filename,
                "metadata": dict(attachment.metadata),
            }
            for attachment in message.attachments
        ],
        "data": dict(message.data or {}),
        "name": message.name,
        "mark": message.mark.value,
        "id": message.id,
        **message.metadata,
    }
    return content, metadata


def _record_to_message(record: Any) -> Message:
    """Deserialize storage record to Message (RawRecord has id, content, metadata)."""
    meta = getattr(record, "metadata", {}) or {}
    attachments_raw = meta.get("attachments")
    attachments = AttachmentRef.coerce_many(attachments_raw if isinstance(attachments_raw, list) else [])
    data_raw = meta.get("data")
    return Message(
        role=meta.get("role", MessageRole.USER),
        kind=meta.get("kind", MessageKind.CHAT),
        text=meta.get("text", getattr(record, "content", "")),
        attachments=attachments,
        data=dict(data_raw) if isinstance(data_raw, dict) else None,
        name=meta.get("name"),
        metadata={
            k: v
            for k, v in meta.items()
            if k not in ("role", "kind", "text", "attachments", "data", "name", "mark", "id")
        },
        mark=meta.get("mark", MessageMark.TEMPORARY),
        id=meta.get("id"),
    )


class RawDataLongTermMemory(ILongTermMemory):
    """Long-term memory backed by knowledge raw data storage (substring search, no embedding).

    Persists Message as content + metadata (role, name, etc.); get() searches by substring
    in content and returns matching records as Messages.
    """

    def __init__(self, storage: IRawDataStore, name: str = "rawdata_ltm") -> None:
        self._storage = storage
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def component_type(self) -> Literal[ComponentType.MEMORY]:
        return ComponentType.MEMORY

    def get(self, query: str = "", **kwargs: Any) -> list[Message]:
        top_k = kwargs.get("top_k", 10)
        if not isinstance(top_k, int):
            top_k = 10
        records = self._storage.search(query=query, top_k=top_k)
        return [_record_to_message(r) for r in records]

    async def persist(self, messages: list[Message]) -> None:
        for msg in messages:
            content, metadata = _message_to_content_metadata(msg)
            self._storage.add(content, metadata=metadata)


__all__ = ["RawDataLongTermMemory"]
