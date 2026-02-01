"""In-memory vector store implementation."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from dare_framework.knowledge._internal.vector_knowledge.document import Document
from dare_framework.knowledge._internal.vector_knowledge.vector_store.interfaces import (
    IVectorStore,
)

if TYPE_CHECKING:
    pass


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector.
        vec2: Second vector.

    Returns:
        Cosine similarity score between -1 and 1.
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vectors must have the same length: {len(vec1)} != {len(vec2)}")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


class InMemoryVectorStore(IVectorStore):
    """In-memory vector store for document storage and retrieval.

    Stores documents with their embeddings and supports similarity search.
    Uses cosine similarity for vector comparison.

    Example:
        store = InMemoryVectorStore()
        doc = Document(content="Hello world", embedding=[0.1, 0.2, ...])
        store.add(doc)
        results = store.search(query_embedding=[0.1, 0.2, ...], top_k=5)
    """

    def __init__(self) -> None:
        """Initialize an empty vector store."""
        self._documents: dict[str, Document] = {}
        """Document storage by ID."""

    def add(self, document: Document) -> None:
        """Add a document to the store.

        Args:
            document: Document to add.

        Raises:
            ValueError: If document ID already exists or document has no embedding.
        """
        if document.id in self._documents:
            raise ValueError(f"Document with ID {document.id} already exists")
        if document.embedding is None:
            raise ValueError("Document must have an embedding before adding to store")
        self._documents[document.id] = document

    def add_batch(self, documents: list[Document]) -> None:
        """Add multiple documents to the store.

        Args:
            documents: List of documents to add.

        Raises:
            ValueError: If any document ID already exists or has no embedding.
        """
        for doc in documents:
            self.add(doc)

    def get(self, document_id: str) -> Document | None:
        """Get a document by ID.

        Args:
            document_id: Document identifier.

        Returns:
            Document if found, None otherwise.
        """
        return self._documents.get(document_id)

    def remove(self, document_id: str) -> bool:
        """Remove a document from the store.

        Args:
            document_id: Document identifier.

        Returns:
            True if document was removed, False if not found.
        """
        if document_id in self._documents:
            del self._documents[document_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all documents from the store."""
        self._documents.clear()

    def count(self) -> int:
        """Get the number of documents in the store.

        Returns:
            Number of documents.
        """
        return len(self._documents)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_similarity: float | None = None,
    ) -> list[tuple[Document, float]]:
        """Search for similar documents using cosine similarity.

        Args:
            query_embedding: Query vector to search for.
            top_k: Maximum number of results to return.
            min_similarity: Minimum similarity threshold (optional).

        Returns:
            List of (document, similarity_score) tuples, sorted by similarity (descending).
        """
        if not self._documents:
            return []

        results: list[tuple[Document, float]] = []

        for doc in self._documents.values():
            if doc.embedding is None:
                continue

            similarity = cosine_similarity(query_embedding, doc.embedding)

            if min_similarity is not None and similarity < min_similarity:
                continue

            results.append((doc, similarity))

        # Sort by similarity (descending) and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def list_all(self) -> list[Document]:
        """List all documents in the store.

        Returns:
            List of all documents.
        """
        return list(self._documents.values())


__all__ = ["InMemoryVectorStore", "cosine_similarity"]
