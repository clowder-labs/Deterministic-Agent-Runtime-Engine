"""Embedding domain component interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework.embedding.types import EmbeddingOptions, EmbeddingResult


@runtime_checkable
class IEmbeddingAdapter(Protocol):
    """[Component] Embedding adapter contract for text embedding.

    Usage: Used by knowledge retrieval systems to generate vector embeddings.
    """

    async def embed(
        self,
        text: str,
        *,
        options: EmbeddingOptions | None = None,
    ) -> EmbeddingResult:
        """[Component] Generate embedding for a single text.

        Args:
            text: Text to embed.
            options: Optional embedding options.

        Returns:
            EmbeddingResult containing the embedding vector and metadata.
        """
        ...

    async def embed_batch(
        self,
        texts: list[str],
        *,
        options: EmbeddingOptions | None = None,
    ) -> list[EmbeddingResult]:
        """[Component] Generate embeddings for multiple texts (batch).

        Args:
            texts: List of texts to embed.
            options: Optional embedding options.

        Returns:
            List of EmbeddingResult objects.
        """
        ...


__all__ = ["IEmbeddingAdapter"]
