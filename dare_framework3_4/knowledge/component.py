"""Knowledge domain component interfaces.

Defines IKnowledge for knowledge retrieval (RAG, GraphRAG, etc.).
IKnowledge inherits from IRetrievalContext (defined in context domain).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from dare_framework3_4.context import IRetrievalContext

if TYPE_CHECKING:
    from dare_framework3_4.context import Message


@runtime_checkable
class IKnowledge(IRetrievalContext, Protocol):
    """[Component] Knowledge retrieval interface (RAG/GraphRAG etc).

    Usage: Injected into Context.knowledge.
    Provides retrieval from external knowledge sources.

    Implementation forms:
    - Remote API: Vector DB, Graph DB, enterprise knowledge base
    - Local: File-based index, local vector store
    - MCP: Model Context Protocol (planned, not yet implemented)

    Inherits IRetrievalContext.get().
    """

    def get(self, query: str, **kwargs) -> list["Message"]:
        """Retrieve relevant knowledge based on query.

        Args:
            query: Search query for knowledge retrieval.
            **kwargs: Additional parameters (e.g., top_k, filters).

        Returns:
            List of relevant messages/documents from knowledge base.
        """
        ...


__all__ = ["IKnowledge"]
