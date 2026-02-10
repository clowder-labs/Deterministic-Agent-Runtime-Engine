"""knowledge domain interfaces.

Defines IKnowledge for knowledge retrieval (RAG, GraphRAG, etc.).
IKnowledge inherits from IRetrievalContext (defined in context domain).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from dare_framework.context.kernel import IRetrievalContext

if TYPE_CHECKING:
    from dare_framework.context.types import Message


class IKnowledge(IRetrievalContext, ABC):
    """[Component] Knowledge retrieval interface (RAG/GraphRAG etc).

    Usage: Injected into Context.knowledge.
    Provides retrieval from external knowledge sources.

    Implementation forms:
    - Remote API: Vector DB, Graph DB, enterprise knowledge base
    - Local: File-based index, local vector store
    - MCP: Model Context Protocol (planned, not yet implemented)

    Inherits IRetrievalContext.get(); adds add() for ingesting content.
    """

    @abstractmethod
    def get(self, query: str, **kwargs: Any) -> list[Message]:
        """Retrieve relevant knowledge based on query.

        Args:
            query: Search query for knowledge retrieval.
            **kwargs: Additional parameters (e.g., top_k, filters).

        Returns:
            List of relevant messages/documents from knowledge base.
        """
        ...

    @abstractmethod
    def add(self, content: str, **kwargs: Any) -> None:
        """Add content to the knowledge base.

        Implementation-defined: may index a single document, upsert by ID, etc.
        Callers can pass optional metadata via **kwargs (e.g. metadata={}, auto_embed=True).

        Args:
            content: Text content to add (e.g. one document or one chunk).
            **kwargs: Implementation-specific options (e.g. metadata, auto_embed).
        """
        ...


__all__ = ["IKnowledge"]
