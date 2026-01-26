"""Context domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from dare_framework2.context.types import AssembledContext, IndexStatus, Prompt, RetrievedContext

if TYPE_CHECKING:
    from dare_framework2.execution.types import Budget


class IContextStrategy(Protocol):
    """Strategy for building prompts from assembled context."""

    async def build_prompt(self, assembled: AssembledContext) -> Prompt:
        """Build a prompt from assembled context.

        Args:
            assembled: The assembled context

        Returns:
            The final prompt for the model
        """
        ...


@runtime_checkable
class IMemory(Protocol):
    """Memory interface for retrieval and persistence."""

    async def retrieve(
        self,
        query: str,
        *,
        budget: "Budget | None" = None,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant items matching the query."""
        ...

    async def add(self, items: list[dict[str, Any]]) -> None:
        """Add items to memory storage."""
        ...


@runtime_checkable
class IPromptStore(Protocol):
    """Prompt template storage interface."""

    async def get(self, prompt_id: str) -> str | None:
        """Retrieve a prompt template by ID."""
        ...

    async def set(self, prompt_id: str, content: str) -> None:
        """Store a prompt template."""
        ...


class IRetriever(Protocol):
    """Retrieval component for context engineering."""

    async def retrieve(
        self,
        query: str,
        *,
        budget: "Budget | None" = None,
    ) -> RetrievedContext:
        """Retrieve relevant context for a query."""
        ...


class IIndexer(Protocol):
    """Indexing component for retrieval readiness."""

    async def ensure_index(self, scope: str) -> IndexStatus:
        """Ensure the index for a scope is ready."""
        ...

    async def add(self, scope: str, items: list[dict[str, Any]]) -> None:
        """Add items to the index for a scope."""
        ...
