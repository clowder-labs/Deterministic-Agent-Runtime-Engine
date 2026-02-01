"""SQLite-backed vector store implementation.

Stores documents and embeddings in a single SQLite file; similarity search
computes cosine similarity in Python (no vector index). Suitable for
small to medium datasets.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from dare_framework.knowledge._internal.vector_knowledge.document import Document
from dare_framework.knowledge._internal.vector_knowledge.vector_store.interfaces import (
    IVectorStore,
)
from dare_framework.knowledge._internal.vector_knowledge.vector_store.in_memory_store import (
    cosine_similarity,
)


def _metadata_to_json(metadata: dict[str, Any]) -> str:
    """Serialize metadata dict to JSON string."""
    return json.dumps(metadata, ensure_ascii=False)


def _metadata_from_json(s: str | None) -> dict[str, Any]:
    """Deserialize metadata from JSON string."""
    if not s:
        return {}
    return json.loads(s)


def _embedding_to_json(embedding: list[float]) -> str:
    """Serialize embedding list to JSON string."""
    return json.dumps(embedding)


def _embedding_from_json(s: str | None) -> list[float] | None:
    """Deserialize embedding from JSON string."""
    if not s:
        return None
    return json.loads(s)


class SQLiteVectorStore(IVectorStore):
    """SQLite-backed vector store (single file, persistent).

    Stores id, content, embedding (JSON), metadata (JSON). search() loads
    vectors and computes cosine similarity in Python; no native vector index.
    Use for small/medium datasets; for large scale prefer ChromaDB or similar.
    """

    def __init__(self, db_path: str | Path) -> None:
        """Initialize with database file path.

        Args:
            db_path: Path to SQLite file (e.g. "./vectors.db"). Created if missing.
        """
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_table()

    def _ensure_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_docs (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def _row_to_document(self, row: sqlite3.Row) -> Document:
        emb = _embedding_from_json(row["embedding"])
        meta = _metadata_from_json(row["metadata"])
        return Document(
            id=row["id"],
            content=row["content"] or "",
            embedding=emb,
            metadata=meta,
        )

    def add(self, document: Document) -> None:
        if document.embedding is None:
            raise ValueError("Document must have an embedding before adding to store")
        cur = self._conn.execute(
            "SELECT 1 FROM vector_docs WHERE id = ?", (document.id,)
        ).fetchone()
        if cur is not None:
            raise ValueError(f"Document with ID {document.id} already exists")
        self._conn.execute(
            "INSERT INTO vector_docs (id, content, embedding, metadata) VALUES (?, ?, ?, ?)",
            (
                document.id,
                document.content,
                _embedding_to_json(document.embedding),
                _metadata_to_json(document.metadata),
            ),
        )
        self._conn.commit()

    def add_batch(self, documents: list[Document]) -> None:
        for doc in documents:
            self.add(doc)

    def get(self, document_id: str) -> Document | None:
        row = self._conn.execute(
            "SELECT id, content, embedding, metadata FROM vector_docs WHERE id = ?",
            (document_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_document(row)

    def remove(self, document_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM vector_docs WHERE id = ?", (document_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def clear(self) -> None:
        self._conn.execute("DELETE FROM vector_docs")
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM vector_docs").fetchone()
        return row["n"] if row else 0

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_similarity: float | None = None,
    ) -> list[tuple[Document, float]]:
        rows = self._conn.execute(
            "SELECT id, content, embedding, metadata FROM vector_docs"
        ).fetchall()
        if not rows:
            return []

        results: list[tuple[Document, float]] = []
        for row in rows:
            emb = _embedding_from_json(row["embedding"])
            if emb is None:
                continue
            sim = cosine_similarity(query_embedding, emb)
            if min_similarity is not None and sim < min_similarity:
                continue
            doc = self._row_to_document(row)
            results.append((doc, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def list_all(self) -> list[Document]:
        rows = self._conn.execute(
            "SELECT id, content, embedding, metadata FROM vector_docs"
        ).fetchall()
        return [self._row_to_document(row) for row in rows]

    def close(self) -> None:
        """Close the database connection. Optional."""
        self._conn.close()

    def __enter__(self) -> SQLiteVectorStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = ["SQLiteVectorStore"]
