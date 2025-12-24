from __future__ import annotations

from ..core.interfaces import IMemory


class InMemoryMemory(IMemory):
    def __init__(self) -> None:
        self._items: dict[str, tuple[str, dict]] = {}

    async def store(self, key: str, value: str, metadata: dict | None = None) -> None:
        self._items[key] = (value, metadata or {})

    async def search(self, query: str, top_k: int = 5) -> list:
        matches = []
        for key, (value, metadata) in self._items.items():
            if query in value:
                matches.append((key, value, metadata))
        results = matches[:top_k]
        from ..core.models import MemoryItem

        return [MemoryItem(key=key, value=value, metadata=metadata) for key, value, metadata in results]

    async def get(self, key: str) -> str | None:
        item = self._items.get(key)
        return item[0] if item else None
