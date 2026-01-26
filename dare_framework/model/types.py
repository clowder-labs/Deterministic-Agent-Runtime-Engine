"""Model domain data types and prompt/result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dare_framework.context import Message


@dataclass(frozen=True)
class Prompt:
    """Prompt representation for model adapters."""

    messages: list[Message]
    tools: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    """Model response including optional tool calls."""

    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerateOptions:
    """Generation options for model adapters."""

    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stop: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["Prompt", "ModelResponse", "GenerateOptions"]
