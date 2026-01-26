"""Model domain component interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from dare_framework2.model.types import Message, ModelResponse, GenerateOptions

if TYPE_CHECKING:
    from dare_framework2.tool.types import ToolDefinition


@runtime_checkable
class IModelAdapter(Protocol):
    """Model adapter for LLM inference.
    
    Responsible for translating between the framework's message format
    and the specific LLM provider's API.
    """

    async def generate(
        self,
        messages: list[Message],
        tools: list["ToolDefinition"] | None = None,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        """Generate a response from the model.
        
        Args:
            messages: The conversation history
            tools: Optional list of tool definitions available to the model
            options: Optional generation settings
            
        Returns:
            The model's response, potentially including tool calls
        """
        ...

    async def generate_structured(
        self,
        messages: list[Message],
        output_schema: type[Any],
    ) -> Any:
        """Generate a structured response matching the given schema.
        
        Args:
            messages: The conversation history
            output_schema: The expected output type/schema
            
        Returns:
            An instance of output_schema populated with model output
        """
        ...
