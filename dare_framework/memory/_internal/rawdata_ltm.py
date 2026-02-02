"""Long-term memory implementation backed by raw data storage (IRawDataStore)."""

from __future__ import annotations

from typing import Any, Literal

from dare_framework.context import Message
from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.memory.kernel import ILongTermMemory
from dare_framework.knowledge._internal.rawdata_knowledge.storage.interfaces import (
    IRawDataStore,
)


def _message_to_content_metadata(message: Message) -> tuple[str, dict[str, Any]]:
    """Serialize Message to (content, metadata) for storage. Content must be non-empty."""
    content = message.content if message.content else " "
    metadata: dict[str, Any] = {
        "role": message.role,
        "name": message.name,
        **message.metadata,
    }
    return content, metadata


def _record_to_message(record: Any) -> Message:
    """Deserialize storage record to Message (RawRecord has id, content, metadata)."""
    meta = getattr(record, "metadata", {}) or {}
    return Message(
        role=meta.get("role", "user"),
        content=getattr(record, "content", ""),
        name=meta.get("name"),
        metadata={k: v for k, v in meta.items() if k not in ("role", "name")},
    )


class RawDataLongTermMemory(ILongTermMemory, IComponent):
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
