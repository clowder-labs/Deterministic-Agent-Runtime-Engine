"""Embedding domain data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EmbeddingResult:
    """Embedding result containing vector and metadata."""

    vector: list[float]
    """The embedding vector."""
    metadata: dict[str, Any] = field(default_factory=dict)
    """Optional metadata (e.g., model name, usage info)."""


@dataclass(frozen=True)
class EmbeddingOptions:
    """Options for embedding generation."""

    model: str | None = None
    """Model name to use (if adapter supports multiple models)."""
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional options/metadata."""


__all__ = ["EmbeddingResult", "EmbeddingOptions"]
