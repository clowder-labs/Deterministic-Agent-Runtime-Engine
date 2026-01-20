"""Memory domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dare_framework3_3.context.types import Budget


@runtime_checkable
class IMemory(Protocol):
    """[Component] Memory interface for retrieval and persistence.

    Usage: Injected into the context manager for retrieval operations.
    """

    async def retrieve(
        self,
        query: str,
        *,
        budget: "Budget | None" = None,
    ) -> list[dict[str, Any]]:
        """[Component] Retrieve items matching a query.

        Usage: Called during context assembly or plan evaluation.
        """
        ...

    async def add(self, items: list[dict[str, Any]]) -> None:
        """[Component] Persist items into memory.

        Usage: Called after tool execution or summarization steps.
        """
        ...


@runtime_checkable
class IPromptStore(Protocol):
    """[Component] Prompt template storage interface.

    Usage: Used by prompt builders to fetch reusable templates.
    """

    async def get(self, prompt_id: str) -> str | None:
        """[Component] Fetch a stored prompt template.

        Usage: Called before building prompts.
        """
        ...

    async def set(self, prompt_id: str, content: str) -> None:
        """[Component] Store a prompt template.

        Usage: Called by tooling that manages prompt libraries.
        """
        ...


__all__ = ["IMemory", "IPromptStore"]
