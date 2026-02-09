"""memory domain interfaces.

Defines IShortTermMemory and ILongTermMemory.
Both inherit from IRetrievalContext (defined in context domain).
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Literal

from dare_framework.context.kernel import IRetrievalContext
from dare_framework.infra.component import ComponentType, IComponent

if TYPE_CHECKING:
    from dare_framework.context.types import Message


class IShortTermMemory(IComponent, IRetrievalContext, ABC):
    """[Component] Short-term memory interface (current session).

    Usage: Injected into Context.short_term_memory.
    Holds messages for the current session/conversation.

    Inherits IRetrievalContext.get() and adds add/clear methods.
    """

    @property
    def component_type(self) -> Literal[ComponentType.MEMORY]:
        return ComponentType.MEMORY

    def add(self, message: Message) -> None:
        """Add a message to short-term memory."""
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


class ILongTermMemory(IComponent, IRetrievalContext, ABC):
    """[Component] Long-term memory interface (cross-session persistent).

    Usage: Injected into Context.long_term_memory.
    Provides retrieval from persistent storage.

    Inherits IRetrievalContext.get().
    """

    @property
    def component_type(self) -> Literal[ComponentType.MEMORY]:
        return ComponentType.MEMORY

    async def persist(self, messages: list[Message]) -> None:
        """Persist messages to long-term storage."""
        ...


__all__ = ["IShortTermMemory", "ILongTermMemory"]
