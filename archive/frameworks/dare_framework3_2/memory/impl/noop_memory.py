"""No-op memory implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dare_framework3_2.memory.component import IMemory

if TYPE_CHECKING:
    from dare_framework3_2.context.types import Budget


class NoOpMemory(IMemory):
    """A memory implementation that always returns empty results.
    
    Useful as a default when no memory backend is configured,
    or for testing scenarios that don't require persistence.
    """

    async def retrieve(
        self,
        query: str,
        *,
        budget: "Budget | None" = None,
    ) -> list[dict[str, Any]]:
        """Always returns an empty list."""
        return []

    async def add(self, items: list[dict[str, Any]]) -> None:
        """Does nothing - items are discarded."""
        pass
