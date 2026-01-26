"""OpenAI-compatible embedding adapter using LangChain."""

from __future__ import annotations

import logging
from typing import Any

from dare_framework.embedding.interfaces import IEmbeddingAdapter
from dare_framework.embedding.types import EmbeddingOptions, EmbeddingResult

# Optional LangChain imports
try:
    from langchain_openai import OpenAIEmbeddings
except ImportError:  # pragma: no cover - handled at runtime
    OpenAIEmbeddings = None  # type: ignore[assignment]


class OpenAIEmbeddingAdapter(IEmbeddingAdapter):
    """Embedding adapter for OpenAI-compatible APIs using LangChain.

    Supports OpenAI, Azure OpenAI, and any OpenAI-compatible endpoint (e.g., Qwen).
    Requires the `langchain-openai` package to be installed.

    Args:
        model: The embedding model name (e.g., "text-embedding-3-small", "text-embedding-ada-002")
        api_key: The API key for authentication
        endpoint: Optional custom endpoint URL for self-hosted models (e.g., Qwen API)
        http_client_options: Optional HTTP client configuration
    """

    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        endpoint: str | None = None,
        http_client_options: dict[str, Any] | None = None,
    ) -> None:
        self._model = model or "text-embedding-3-small"
        self._api_key = api_key
        self._endpoint = endpoint
        self._http_client_options = dict(http_client_options or {})
        self._client: Any = None

    async def embed(
        self,
        text: str,
        *,
        options: EmbeddingOptions | None = None,
    ) -> EmbeddingResult:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.
            options: Optional embedding options.

        Returns:
            EmbeddingResult containing the embedding vector and metadata.
        """
        client = self._ensure_client(options)
        embedding = await client.aembed_query(text)
        
        usage = getattr(client, "response_metadata", {}).get("token_usage", {})
        metadata = {
            "model": self._model,
            "usage": usage,
        }
        if options and options.metadata:
            metadata.update(options.metadata)

        return EmbeddingResult(vector=embedding, metadata=metadata)

    async def embed_batch(
        self,
        texts: list[str],
        *,
        options: EmbeddingOptions | None = None,
    ) -> list[EmbeddingResult]:
        """Generate embeddings for multiple texts (batch).

        Args:
            texts: List of texts to embed.
            options: Optional embedding options.

        Returns:
            List of EmbeddingResult objects.
        """
        if not texts:
            return []

        client = self._ensure_client(options)
        embeddings = await client.aembed_documents(texts)
        
        usage = getattr(client, "response_metadata", {}).get("token_usage", {})
        metadata = {
            "model": self._model,
            "usage": usage,
        }
        if options and options.metadata:
            metadata.update(options.metadata)

        return [
            EmbeddingResult(vector=emb, metadata=metadata) for emb in embeddings
        ]

    def _ensure_client(self, options: EmbeddingOptions | None = None) -> Any:
        """Ensure the LangChain client is initialized."""
        if self._client is None:
            self._client = self._build_client(options)
        return self._client

    def _build_client(self, options: EmbeddingOptions | None = None) -> Any:
        """Build the LangChain OpenAIEmbeddings client."""
        if OpenAIEmbeddings is None:
            raise RuntimeError("langchain-openai is required for OpenAIEmbeddingAdapter")

        model = (options.model if options else None) or self._model
        kwargs: dict[str, Any] = {"model": model}

        if self._api_key:
            kwargs["api_key"] = self._api_key
        elif self._endpoint:
            # Local/self-hosted endpoints still require a key; use placeholder
            kwargs["api_key"] = "dummy-key"

        if self._endpoint:
            kwargs["base_url"] = self._endpoint

        sync_client, async_client = self._build_http_clients()
        if sync_client is not None:
            kwargs["http_client"] = sync_client
        if async_client is not None:
            kwargs["http_async_client"] = async_client

        return OpenAIEmbeddings(**kwargs)

    def _build_http_clients(self) -> tuple[Any | None, Any | None]:
        """Build custom HTTP clients if options are provided."""
        if not self._http_client_options:
            return None, None
        try:
            import httpx
        except Exception:
            return None, None
        try:
            opts = dict(self._http_client_options)
            sync_client = httpx.Client(**opts)
            async_client = httpx.AsyncClient(**opts)
            return sync_client, async_client
        except Exception:
            return None, None


__all__ = ["OpenAIEmbeddingAdapter"]
