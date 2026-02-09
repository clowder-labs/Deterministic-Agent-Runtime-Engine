"""In-memory short-term memory implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework.memory.kernel import IShortTermMemory

if TYPE_CHECKING:
    from dare_framework.context import Message


class InMemorySTM(IShortTermMemory):
    """In-memory short-term memory implementation.

    Simple list-based storage for current session messages.
    Implements IShortTermMemory (which inherits IRetrievalContext).
    """

    @property
    def name(self) -> str:
        return "in_memory_stm"

    def __init__(self) -> None:
        self._messages: list[Message] = []

    def add(self, message: Message) -> None:
        """Add a message to memory."""
        self._messages.append(message)

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()

    def get(self, query: str = "", **kwargs) -> list[Message]:
        """Retrieve all messages (implements IRetrievalContext.get).

        For short-term memory, query is ignored - returns all messages.
        """
        return list(self._messages)

    def compress(self, max_messages: int | None = None, **kwargs) -> int:
        """Compress short-term memory by keeping only the most recent messages.

        Args:
            max_messages: Maximum number of messages to keep (keeps most recent).
                          If None, no compression is performed.
            **kwargs: Additional compression parameters (unused for now).

        Returns:
            Number of messages removed.
        """
        if max_messages is None or len(self._messages) <= max_messages:
            return 0

        removed_count = len(self._messages) - max_messages
        # Keep the most recent messages
        self._messages = self._messages[-max_messages:]
        return removed_count


__all__ = ["InMemorySTM"]
