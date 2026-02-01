"""ChromaDB-backed vector store implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from dare_framework.knowledge._internal.vector_knowledge.document import Document
from dare_framework.knowledge._internal.vector_knowledge.vector_store.interfaces import (
    IVectorStore,
)

if TYPE_CHECKING:
    pass


def _metadata_to_chromadb(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Convert document metadata to ChromaDB-compatible types (str, int, float, bool).

    Non-primitive values are JSON-serialized to strings.
    """
    result: dict[str, str | int | float | bool] = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            result[k] = v
        else:
            result[k] = json.dumps(v, default=str)
    return result


def _metadata_from_chromadb(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Convert ChromaDB metadata back to document metadata. No deserialization by default."""
    if not metadata:
        return {}
    return dict(metadata)


class ChromaDBVectorStore(IVectorStore):
    """ChromaDB-backed vector store for document storage and retrieval.

    ChromaDB is a dedicated vector database: it stores embeddings and performs
    similarity search internally. We do not compute cosine distance in Python;
    the collection is created with metadata={"hnsw:space": "cosine"}, so ChromaDB
    uses cosine distance (1 - cosine_similarity) in its HNSW index. query() returns
    distances; we convert to similarity in search() via similarity = 1 - distance.

    What ChromaDB can store (per item): id, embedding (required for search), document
    text (we map to Document.content), and metadatas (str/int/float/bool only; we
    JSON-serialize other types to str). It is not a general-purpose DB: every row
    must have an embedding for similarity search; use a separate store for pure
    key-value or relational data.

    Persists documents and embeddings in ChromaDB (local or server).

    Example:
        store = ChromaDBVectorStore(collection_name="my_kb", path="./chroma_data")
        doc = Document(content="Hello world", embedding=[0.1, 0.2, ...])
        store.add(doc)
        results = store.search(query_embedding=[0.1, 0.2, ...], top_k=5)
    """

    def __init__(
        self,
        collection_name: str = "dare_vector_knowledge",
        path: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        """Initialize ChromaDB vector store.

        Args:
            collection_name: ChromaDB collection name (default: "dare_vector_knowledge").
            path: For persistent client, directory path; if None and no host, uses in-memory.
            host: ChromaDB server host (HTTP client). If set, port can be specified.
            port: ChromaDB server port (default 8000 when host is set).
        """
        import chromadb
        from chromadb.config import Settings

        self._collection_name = collection_name

        if host is not None:
            # HTTP client: connect to remote ChromaDB server
            self._client = chromadb.HttpClient(
                host=host,
                port=port or 8000,
                settings=Settings(anonymized_telemetry=False),
            )
        elif path is not None:
            # Persistent client: local directory
            self._client = chromadb.PersistentClient(
                path=path,
                settings=Settings(anonymized_telemetry=False),
            )
        else:
            # Ephemeral in-memory client (no persistence)
            self._client = chromadb.EphemeralClient(
                settings=Settings(anonymized_telemetry=False),
            )

        # ChromaDB 内部使用余弦距离：hnsw:space="cosine" 指定 HNSW 索引的度量，
        # query() 时由 ChromaDB 计算并返回 distances，我们在 search() 里转为 similarity。
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, document: Document) -> None:
        """Add a document to the store.

        Args:
            document: Document to add.

        Raises:
            ValueError: If document ID already exists or document has no embedding.
        """
        if document.embedding is None:
            raise ValueError("Document must have an embedding before adding to store")

        # ChromaDB upsert overwrites by id; we match InMemoryVectorStore semantics (add = reject duplicate)
        existing = self._collection.get(ids=[document.id], include=[])
        if existing and existing["ids"]:
            raise ValueError(f"Document with ID {document.id} already exists")

        meta = _metadata_to_chromadb(document.metadata)
        self._collection.add(
            ids=[document.id],
            embeddings=[document.embedding],
            documents=[document.content],
            metadatas=[meta],
        )

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
        result = self._collection.get(
            ids=[document_id],
            include=["embeddings", "documents", "metadatas"],
        )
        if not result["ids"]:
            return None
        doc = result["documents"][0]
        meta = result["metadatas"][0] if result["metadatas"] else {}
        emb = result["embeddings"][0] if result["embeddings"] else None
        return Document(
            id=document_id,
            content=doc or "",
            embedding=emb,
            metadata=_metadata_from_chromadb(meta),
        )

    def remove(self, document_id: str) -> bool:
        """Remove a document from the store.

        Args:
            document_id: Document identifier.

        Returns:
            True if document was removed, False if not found.
        """
        existing = self._collection.get(ids=[document_id], include=[])
        if not existing["ids"]:
            return False
        self._collection.delete(ids=[document_id])
        return True

    def clear(self) -> None:
        """Clear all documents from the store by deleting and recreating the collection."""
        self._client.delete_collection(name=self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """Get the number of documents in the store.

        Returns:
            Number of documents.
        """
        return self._collection.count()

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_similarity: float | None = None,
    ) -> list[tuple[Document, float]]:
        """Search for similar documents using cosine similarity.

        ChromaDB (with hnsw:space=cosine) computes cosine distance = 1 - cosine_similarity
        internally; query() returns distances. We convert to similarity via similarity = 1 - distance.

        Args:
            query_embedding: Query vector to search for.
            top_k: Maximum number of results to return.
            min_similarity: Minimum similarity threshold (optional).

        Returns:
            List of (document, similarity_score) tuples, sorted by similarity (descending).
        """
        n = min(top_k, self.count()) if min_similarity is None else self.count()
        if n <= 0:
            return []

        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            include=["embeddings", "documents", "metadatas", "distances"],
        )
        if not result["ids"] or not result["ids"][0]:
            return []

        ids = result["ids"][0]
        docs = result["documents"][0]
        metadatas = result["metadatas"][0] if result["metadatas"] else []
        embeddings = result["embeddings"][0] if result["embeddings"] else []
        distances = result["distances"][0] if result["distances"] else []

        # ChromaDB cosine distance = 1 - cosine_similarity, so similarity = 1 - distance.
        out: list[tuple[Document, float]] = []
        for i, doc_id in enumerate(ids):
            dist = distances[i] if i < len(distances) else 0.0
            similarity = 1.0 - dist
            if min_similarity is not None and similarity < min_similarity:
                continue
            doc_content = docs[i] if i < len(docs) else ""
            meta = metadatas[i] if i < len(metadatas) else {}
            emb = embeddings[i] if i < len(embeddings) else None
            doc = Document(
                id=doc_id,
                content=doc_content,
                embedding=emb,
                metadata=_metadata_from_chromadb(meta),
            )
            out.append((doc, similarity))

        out.sort(key=lambda x: x[1], reverse=True)
        return out[:top_k]

    def list_all(self) -> list[Document]:
        """List all documents in the store.

        Returns:
            List of all documents.
        """
        result = self._collection.get(
            include=["embeddings", "documents", "metadatas"],
        )
        if not result["ids"]:
            return []
        out: list[Document] = []
        for i, doc_id in enumerate(result["ids"]):
            doc_content = result["documents"][i] if result["documents"] else ""
            meta = result["metadatas"][i] if result["metadatas"] and i < len(result["metadatas"]) else {}
            emb = result["embeddings"][i] if result["embeddings"] and i < len(result["embeddings"]) else None
            out.append(
                Document(
                    id=doc_id,
                    content=doc_content,
                    embedding=emb,
                    metadata=_metadata_from_chromadb(meta),
                )
            )
        return out


__all__ = ["ChromaDBVectorStore"]
