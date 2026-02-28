from __future__ import annotations

import pytest

import dare_framework.embedding._internal.openai_embedding as openai_embedding_module
from dare_framework.embedding import EmbeddingOptions
from dare_framework.embedding._internal.openai_embedding import OpenAIEmbeddingAdapter


class _FakeEmbeddings:
    last_kwargs: dict[str, object] | None = None

    def __init__(self, **kwargs: object) -> None:
        type(self).last_kwargs = dict(kwargs)
        self.response_metadata = {"token_usage": {"total_tokens": 42}}

    async def aembed_query(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(i), float(len(text))] for i, text in enumerate(texts, start=1)]


def test_build_client_requires_langchain_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_embedding_module, "OpenAIEmbeddings", None)
    adapter = OpenAIEmbeddingAdapter(model="test-model")

    with pytest.raises(RuntimeError, match="langchain-openai"):
        adapter._build_client()


@pytest.mark.asyncio
async def test_embed_returns_vector_and_merged_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_embedding_module, "OpenAIEmbeddings", _FakeEmbeddings)

    adapter = OpenAIEmbeddingAdapter(model="embedding-small", api_key="secret")
    result = await adapter.embed(
        "hello",
        options=EmbeddingOptions(metadata={"trace_id": "trace-1"}),
    )

    assert result.vector == [5.0, 1.0]
    assert result.metadata["model"] == "embedding-small"
    assert result.metadata["usage"] == {"total_tokens": 42}
    assert result.metadata["trace_id"] == "trace-1"


@pytest.mark.asyncio
async def test_embed_batch_short_circuits_when_empty() -> None:
    adapter = OpenAIEmbeddingAdapter(model="embedding-small")

    result = await adapter.embed_batch([])

    assert result == []
    assert adapter._client is None


@pytest.mark.asyncio
async def test_embed_batch_returns_results_with_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_embedding_module, "OpenAIEmbeddings", _FakeEmbeddings)

    adapter = OpenAIEmbeddingAdapter(model="embedding-small", api_key="secret")
    results = await adapter.embed_batch(["a", "abc"])

    assert len(results) == 2
    assert results[0].vector == [1.0, 1.0]
    assert results[1].vector == [2.0, 3.0]
    assert all(item.metadata["usage"] == {"total_tokens": 42} for item in results)


def test_build_client_uses_endpoint_and_dummy_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_embedding_module, "OpenAIEmbeddings", _FakeEmbeddings)

    adapter = OpenAIEmbeddingAdapter(model="embedding-small", endpoint="http://localhost:1234/v1")
    client = adapter._build_client(options=EmbeddingOptions(model="override-model"))

    assert isinstance(client, _FakeEmbeddings)
    assert _FakeEmbeddings.last_kwargs is not None
    assert _FakeEmbeddings.last_kwargs["model"] == "override-model"
    assert _FakeEmbeddings.last_kwargs["base_url"] == "http://localhost:1234/v1"
    assert _FakeEmbeddings.last_kwargs["api_key"] == "dummy-key"
