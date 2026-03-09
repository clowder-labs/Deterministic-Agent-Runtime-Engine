"""Raw data knowledge retrieval implementation (IKnowledge, no embeddings)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dare_framework.context import Message
from dare_framework.knowledge.kernel import IKnowledge
from dare_framework.knowledge._internal.rawdata_knowledge.storage.interfaces import (
    IRawDataStore,
)
from dare_framework.knowledge._internal.rawdata_knowledge.storage.in_memory_storage import (
    InMemoryRawDataStorage,
)

if TYPE_CHECKING:
    pass  # Message imported above for runtime


class RawDataKnowledge(IKnowledge):
    """Raw data knowledge base: stores content + metadata only (no embeddings).

    Implements IKnowledge: add() writes to raw storage; get() searches by
    substring in content and returns matching records as Messages. Use
    InMemoryRawDataStorage or SQLiteRawDataStorage for persistence.

    Example:
        store = InMemoryRawDataStorage()
        knowledge = RawDataKnowledge(storage=store)
        knowledge.add("Python is a language", metadata={"source": "doc1"})
        results = knowledge.get("Python", top_k=5)
    """

    def __init__(self, storage: IRawDataStore | None = None) -> None:
        """Initialize raw data knowledge.

        Args:
            storage: Raw data store (InMemoryRawDataStorage or SQLiteRawDataStorage).
                Creates InMemoryRawDataStorage if None.
        """
        self._storage = storage or InMemoryRawDataStorage()

    def add(self, content: str, **kwargs: Any) -> None:
        """Add content to the raw knowledge base (IKnowledge.add).

        Args:
            content: Text content to store.
            **kwargs: metadata (dict) optional.
        """
        metadata = kwargs.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        self._storage.add(content, metadata=metadata)

    def get(self, query: str = "", **kwargs: Any) -> list[Message]:
        """Retrieve raw knowledge by substring in content.

        No semantic search; matches query as substring in content.
        Returns list of Message (role=assistant, text=record.content, metadata).

        Args:
            query: Substring to match in content; empty returns recent records.
            **kwargs: top_k (int, default 5).

        Returns:
            List of messages from matching raw records.
        """
        top_k = kwargs.get("top_k", 5)
        if not isinstance(top_k, int):
            top_k = 5
        records = self._storage.search(query=query, top_k=top_k)
        messages: list[Message] = []
        for r in records:
            name = r.metadata.get("source") or r.id
            messages.append(
                Message(
                    role="assistant",
                    text=r.content,
                    name=name,
                    metadata={**r.metadata, "document_id": r.id},
                )
            )
        return messages

    def remove(self, record_id: str) -> bool:
        """Remove a raw record by id.

        Args:
            record_id: Record identifier.

        Returns:
            True if removed, False if not found.
        """
        return self._storage.remove(record_id)

    def clear(self) -> None:
        """Remove all raw records."""
        self._storage.clear()

    @property
    def record_count(self) -> int:
        """Number of raw records in the store."""
        return self._storage.count()


__all__ = ["RawDataKnowledge"]
