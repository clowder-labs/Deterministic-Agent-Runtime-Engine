"""embedding domain facade."""

from dare_framework.embedding.interfaces import IEmbeddingAdapter
from dare_framework.embedding.types import EmbeddingOptions, EmbeddingResult
from dare_framework.embedding.defaults import OpenAIEmbeddingAdapter

__all__ = [
    "IEmbeddingAdapter",
    "EmbeddingOptions",
    "EmbeddingResult",
    "OpenAIEmbeddingAdapter",
]
