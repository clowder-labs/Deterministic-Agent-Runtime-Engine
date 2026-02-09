"""Factory to build IKnowledge from config (type + storage + options)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

from dare_framework.knowledge.kernel import IKnowledge
from dare_framework.knowledge.types import KnowledgeConfig

if TYPE_CHECKING:
    from dare_framework.embedding import IEmbeddingAdapter


def create_knowledge(
    config: dict[str, Any] | KnowledgeConfig,
    embedding_adapter: IEmbeddingAdapter | None = None,
) -> IKnowledge | None:
    """Build IKnowledge from config.

    Config schema:
    - type: "vector" | "rawdata"
    - storage: "in_memory" | "sqlite" | "chromadb" (chromadb only for vector)
    - options (or flat keys): path, host, port, collection_name

    For type "vector", embedding_adapter is required (for embedding and search).
    For type "rawdata", embedding_adapter is ignored.

    Returns:
        IKnowledge instance, or None if config is empty/invalid or vector type
        without embedding_adapter.
    """
    if isinstance(config, dict) and not config:
        return None
    cfg = KnowledgeConfig.from_dict(config) if isinstance(config, dict) else config

    if cfg.type == "rawdata":
        return _create_rawdata_knowledge(cfg)
    if cfg.type == "vector":
        return _create_vector_knowledge(cfg, embedding_adapter)
    return None


def _create_rawdata_knowledge(cfg: KnowledgeConfig) -> IKnowledge:
    from dare_framework.knowledge._internal.rawdata_knowledge import (
        InMemoryRawDataStorage,
        RawDataKnowledge,
        SQLiteRawDataStorage,
    )

    opts = cfg.options
    if cfg.storage == "sqlite":
        path = opts.get("path") or ".dare/rawdata.db"
        store = SQLiteRawDataStorage(Path(path))
    else:
        store = InMemoryRawDataStorage()
    return RawDataKnowledge(storage=store)


def _create_vector_knowledge(
    cfg: KnowledgeConfig,
    embedding_adapter: IEmbeddingAdapter | None,
) -> IKnowledge | None:
    if embedding_adapter is None:
        return None
    from dare_framework.knowledge._internal.vector_knowledge import VectorKnowledge
    from dare_framework.knowledge._internal.vector_knowledge.vector_store import (
        ChromaDBVectorStore,
        InMemoryVectorStore,
        SQLiteVectorStore,
    )

    opts = cfg.options
    if cfg.storage == "chromadb":
        path = opts.get("path")
        host = opts.get("host")
        port = opts.get("port")
        collection_name = opts.get("collection_name") or "dare_vector_knowledge"
        store = ChromaDBVectorStore(
            collection_name=collection_name,
            path=str(path) if path else None,
            host=str(host) if host else None,
            port=int(port) if port is not None else None,
        )
    elif cfg.storage == "sqlite":
        path = opts.get("path") or ".dare/vectors.db"
        store = SQLiteVectorStore(Path(path))
    else:
        store = InMemoryVectorStore()
    return VectorKnowledge(embedding_adapter=embedding_adapter, vector_store=store)


__all__ = ["create_knowledge"]
