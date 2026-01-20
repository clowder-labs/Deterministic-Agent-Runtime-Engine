"""Model domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from dare_framework3.model.types import ModelResponse, GenerateOptions

if TYPE_CHECKING:
    from dare_framework3.context.types import Message
    from dare_framework3.tool.types import ToolDefinition


@runtime_checkable
class IModelAdapter(Protocol):
    """Model adapter for LLM inference."""

    async def generate(
        self,
        messages: list["Message"],
        tools: list["ToolDefinition"] | None = None,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        ...

    async def generate_structured(
        self,
        messages: list["Message"],
        output_schema: type[Any],
    ) -> Any:
        ...


__all__ = ["IModelAdapter"]
