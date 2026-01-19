"""Model adapter contracts used by the execute loop (v2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from dare_framework.contracts.tool import ToolDefinition


@dataclass(frozen=True)
class Message:
    """A canonical chat message representation exchanged with model adapters."""

    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class GenerateOptions:
    """Optional generation settings for model adapters."""

    max_tokens: int | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class ModelResponse:
    """Model output including optional tool calls."""

    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class IModelAdapter(Protocol):
    """Model adapter for LLM inference (Layer 2 capability)."""

    async def generate(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        options: GenerateOptions | None = None,
    ) -> ModelResponse: ...

    async def generate_structured(self, messages: list[Message], output_schema: type[Any]) -> Any: ...

