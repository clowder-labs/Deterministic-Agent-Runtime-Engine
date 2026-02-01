"""In-memory raw data storage implementation."""

from __future__ import annotations

import uuid
from typing import Any

from dare_framework.knowledge._internal.rawdata_knowledge.storage.interfaces import (
    IRawDataStore,
    RawRecord,
)


class InMemoryRawDataStorage(IRawDataStore):
    """In-memory raw data store (no persistence)."""

    def __init__(self) -> None:
        self._records: dict[str, RawRecord] = {}

    def add(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        if not content:
            raise ValueError("Content cannot be empty")
        rid = str(uuid.uuid4())
        self._records[rid] = RawRecord(id=rid, content=content, metadata=metadata or {})
        return rid

    def get(self, record_id: str) -> RawRecord | None:
        return self._records.get(record_id)

    def remove(self, record_id: str) -> bool:
        if record_id in self._records:
            del self._records[record_id]
            return True
        return False

    def clear(self) -> None:
        self._records.clear()

    def count(self) -> int:
        return len(self._records)

    def search(self, query: str = "", top_k: int = 100) -> list[RawRecord]:
        if not query:
            return list(self._records.values())[:top_k]
        out = [r for r in self._records.values() if query in r.content]
        return out[:top_k]

    def list_all(self) -> list[RawRecord]:
        return list(self._records.values())


__all__ = ["InMemoryRawDataStorage"]
