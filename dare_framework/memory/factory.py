"""Factory to build ILongTermMemory from config (type + storage + options)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

from dare_framework.memory.kernel import ILongTermMemory
from dare_framework.memory.types import LongTermMemoryConfig

if TYPE_CHECKING:
    from dare_framework.embedding import IEmbeddingAdapter


def create_long_term_memory(
    config: dict[str, Any] | LongTermMemoryConfig,
    embedding_adapter: IEmbeddingAdapter | None = None,
) -> ILongTermMemory | None:
    """Build ILongTermMemory from config.

    Config schema:
    - type: "vector" | "rawdata"
    - storage: "in_memory" | "sqlite" | "chromadb" (chromadb only for vector)
    - options (or flat keys): path, host, port, collection_name

    For type "vector", embedding_adapter is required.
    For type "rawdata", embedding_adapter is ignored.

    Returns:
        ILongTermMemory instance, or None if config is empty/invalid or vector
        type without embedding_adapter.
    """
    if isinstance(config, dict) and not config:
        return None
    cfg = LongTermMemoryConfig.from_dict(config) if isinstance(config, dict) else config

    if cfg.type == "rawdata":
        return _create_rawdata_ltm(cfg)
    if cfg.type == "vector":
        return _create_vector_ltm(cfg, embedding_adapter)
    return None


def _create_rawdata_ltm(cfg: LongTermMemoryConfig) -> ILongTermMemory:
    from dare_framework.memory._internal.rawdata_ltm import RawDataLongTermMemory
    from dare_framework.knowledge._internal.rawdata_knowledge.storage import (
        InMemoryRawDataStorage,
        SQLiteRawDataStorage,
    )

    opts = cfg.options
    if cfg.storage == "sqlite":
        path = opts.get("path") or ".dare/ltm_rawdata.db"
        store = SQLiteRawDataStorage(Path(path))
    else:
        store = InMemoryRawDataStorage()
    return RawDataLongTermMemory(storage=store)


def _create_vector_ltm(
    cfg: LongTermMemoryConfig,
    embedding_adapter: IEmbeddingAdapter | None,
) -> ILongTermMemory | None:
    if embedding_adapter is None:
        return None
    from dare_framework.memory._internal.vector_ltm import VectorLongTermMemory
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
        collection_name = opts.get("collection_name") or "dare_ltm_vectors"
        store = ChromaDBVectorStore(
            collection_name=collection_name,
            path=str(path) if path else None,
            host=str(host) if host else None,
            port=int(port) if port is not None else None,
        )
    elif cfg.storage == "sqlite":
        path = opts.get("path") or ".dare/ltm_vectors.db"
        store = SQLiteVectorStore(Path(path))
    else:
        store = InMemoryVectorStore()
    return VectorLongTermMemory(embedding_adapter=embedding_adapter, vector_store=store)


__all__ = ["create_long_term_memory"]
