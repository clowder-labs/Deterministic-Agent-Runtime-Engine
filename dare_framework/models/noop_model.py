from __future__ import annotations

from dataclasses import dataclass

from dare_framework.components.interfaces import IModelAdapter
from dare_framework.core.models import GenerateOptions, Message, ModelResponse, ToolDefinition


@dataclass
class NoopModelAdapter(IModelAdapter):
    response_text: str = "done"

    async def generate(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        return ModelResponse(content=self.response_text, tool_calls=[])

    async def generate_structured(self, messages: list[Message], output_schema: type) -> object:
        try:
            return output_schema()
        except Exception as exc:
            raise ValueError("Output schema could not be instantiated") from exc
