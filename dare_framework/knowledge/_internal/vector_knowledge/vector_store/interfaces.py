"""Vector store interface for document storage and similarity search."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dare_framework.knowledge._internal.vector_knowledge.document import Document


class IVectorStore(ABC):
    """Abstract interface for vector stores.

    Implement this interface to plug in custom backends (e.g. Pinecone, Qdrant,
    in-memory, ChromaDB). VectorKnowledge accepts any IVectorStore implementation.

    Example:
        class MyVectorStore(IVectorStore):
            def add(self, document: Document) -> None: ...
            def add_batch(self, documents: list[Document]) -> None: ...
            def get(self, document_id: str) -> Document | None: ...
            def remove(self, document_id: str) -> bool: ...
            def clear(self) -> None: ...
            def count(self) -> int: ...
            def search(self, query_embedding, top_k, min_similarity) -> list[tuple[Document, float]]: ...
            def list_all(self) -> list[Document]: ...
    """

    @abstractmethod
    def add(self, document: Document) -> None:
        """Add a document to the store.

        Args:
            document: Document to add (must have embedding set).

        Raises:
            ValueError: If document ID already exists or document has no embedding.
        """
        ...

    @abstractmethod
    def add_batch(self, documents: list[Document]) -> None:
        """Add multiple documents to the store.

        Args:
            documents: List of documents to add.

        Raises:
            ValueError: If any document ID already exists or has no embedding.
        """
        ...

    @abstractmethod
    def get(self, document_id: str) -> Document | None:
        """Get a document by ID.

        Args:
            document_id: Document identifier.

        Returns:
            Document if found, None otherwise.
        """
        ...

    @abstractmethod
    def remove(self, document_id: str) -> bool:
        """Remove a document from the store.

        Args:
            document_id: Document identifier.

        Returns:
            True if document was removed, False if not found.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all documents from the store."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Get the number of documents in the store.

        Returns:
            Number of documents.
        """
        ...

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_similarity: float | None = None,
    ) -> list[tuple[Document, float]]:
        """Search for similar documents (e.g. by cosine similarity).

        Args:
            query_embedding: Query vector.
            top_k: Maximum number of results.
            min_similarity: Optional minimum similarity threshold.

        Returns:
            List of (document, similarity_score) tuples, sorted by similarity descending.
        """
        ...

    @abstractmethod
    def list_all(self) -> list[Document]:
        """List all documents in the store.

        Returns:
            List of all documents.
        """
        ...


__all__ = ["IVectorStore"]
