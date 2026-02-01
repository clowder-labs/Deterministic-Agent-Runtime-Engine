"""Raw data storage interface for rawdata knowledge."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


@dataclass
class RawRecord:
    """Single raw document record (no embedding)."""

    id: str
    """Unique identifier."""

    content: str
    """Text content."""

    metadata: dict[str, Any]
    """Optional metadata (e.g. source, title)."""


class IRawDataStore(ABC):
    """Abstract interface for raw data storage.

    Stores content + metadata only (no embeddings). Implement this to plug
    InMemoryRawDataStorage, SQLiteRawDataStorage, or custom backends.
    """

    @abstractmethod
    def add(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Add raw content and return its id.

        Args:
            content: Text content to store.
            metadata: Optional metadata dict.

        Returns:
            Assigned record id.
        """
        ...

    @abstractmethod
    def get(self, record_id: str) -> RawRecord | None:
        """Get a record by id.

        Args:
            record_id: Record identifier.

        Returns:
            RawRecord if found, None otherwise.
        """
        ...

    @abstractmethod
    def remove(self, record_id: str) -> bool:
        """Remove a record by id.

        Args:
            record_id: Record identifier.

        Returns:
            True if removed, False if not found.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all records."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return number of records."""
        ...

    @abstractmethod
    def search(
        self,
        query: str = "",
        top_k: int = 100,
    ) -> list[RawRecord]:
        """Search by substring in content; empty query returns recent records.

        Args:
            query: Substring to match in content (case-sensitive or impl-defined).
            top_k: Maximum number of results.

        Returns:
            List of matching RawRecords, order impl-defined.
        """
        ...

    @abstractmethod
    def list_all(self) -> list[RawRecord]:
        """Return all records. Order impl-defined."""
        ...


__all__ = ["IRawDataStore", "RawRecord"]
