"""Memory domain component interfaces (Protocol definitions)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from dare_framework3_2.context.types import Budget


@runtime_checkable
class IMemory(Protocol):
    """Memory interface for retrieval and persistence.
    
    Provides a surface for context engineering to store and retrieve
    historical information, facts, and context.
    """

    async def retrieve(
        self,
        query: str,
        *,
        budget: "Budget | None" = None,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant items matching the query.
        
        Args:
            query: The search query
            budget: Optional budget constraints for the retrieval
            
        Returns:
            A list of matching items as dictionaries
        """
        ...

    async def add(self, items: list[dict[str, Any]]) -> None:
        """Add items to memory storage.
        
        Args:
            items: List of items to store
        """
        ...


@runtime_checkable
class IPromptStore(Protocol):
    """Prompt template storage interface.
    
    Provides access to prompt templates and snippets by ID.
    """

    async def get(self, prompt_id: str) -> str | None:
        """Retrieve a prompt template by ID.
        
        Args:
            prompt_id: The unique identifier of the prompt
            
        Returns:
            The prompt template string, or None if not found
        """
        ...

    async def set(self, prompt_id: str, content: str) -> None:
        """Store a prompt template.
        
        Args:
            prompt_id: The unique identifier for the prompt
            content: The prompt template content
        """
        ...
