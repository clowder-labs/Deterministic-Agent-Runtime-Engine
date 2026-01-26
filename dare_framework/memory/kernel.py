"""memory domain interfaces.

Defines IShortTermMemory and ILongTermMemory.
Both inherit from IRetrievalContext (defined in context domain).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from dare_framework.context import IRetrievalContext
from dare_framework.infra.component import ComponentType, IComponent

if TYPE_CHECKING:
    from dare_framework.context import Message


@runtime_checkable
class IShortTermMemory(IComponent, IRetrievalContext, Protocol):
    """[Component] Short-term memory interface (current session).

    Usage: Injected into Context.short_term_memory.
    Holds messages for the current session/conversation.

    Inherits IRetrievalContext.get() and adds add/clear methods.
    """

    @property
    def component_type(self) -> Literal[ComponentType.MEMORY]:
        ...

    def add(self, message: "Message") -> None:
        """Add a message to short-term memory."""
        ...

    def get(self, query: str = "", **kwargs) -> list["Message"]:
        """Get messages (implements IRetrievalContext).

        For STM, query is typically ignored - returns all messages.
        """
        ...

    def clear(self) -> None:
        """Clear all messages from short-term memory."""
        ...

    def compress(self, max_messages: int | None = None, **kwargs) -> int:
        """Compress short-term memory to fit context limits.

        Args:
            max_messages: Maximum number of messages to keep (keeps most recent).
                          If None, uses default compression strategy.
            **kwargs: Additional compression parameters.

        Returns:
            Number of messages removed.
        """
        ...


@runtime_checkable
class ILongTermMemory(IComponent, IRetrievalContext, Protocol):
    """[Component] Long-term memory interface (cross-session persistent).

    Usage: Injected into Context.long_term_memory.
    Provides retrieval from persistent storage.

    Inherits IRetrievalContext.get().
    """

    @property
    def component_type(self) -> Literal[ComponentType.MEMORY]:
        ...

    def get(self, query: str, **kwargs) -> list["Message"]:
        """Retrieve relevant memories based on query.

        Args:
            query: Search query for retrieval.
            **kwargs: Additional parameters (e.g., top_k).

        Returns:
            List of relevant messages from long-term storage.
        """
        ...

    async def persist(self, messages: list["Message"]) -> None:
        """Persist messages to long-term storage."""
        ...


__all__ = ["IShortTermMemory", "ILongTermMemory"]
