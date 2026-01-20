"""Mock model adapter for testing."""

from __future__ import annotations

from typing import Any, Iterable

from dare_framework3.model.interfaces import IModelAdapter
from dare_framework3.model.types import Message, ModelResponse


class MockModelAdapter(IModelAdapter):
    """A mock model adapter that returns predefined responses.
    
    Useful for testing and development without requiring actual LLM calls.
    
    Args:
        responses: An iterable of response strings to return in sequence.
                   When exhausted, returns the last response repeatedly.
    """

    def __init__(self, responses: Iterable[str] | None = None):
        self._responses = list(responses or ["ok"])
        self._index = 0

    async def generate(
        self,
        messages: list[Message],
        tools: Any = None,
        options: Any = None,
    ) -> ModelResponse:
        """Return the next predefined response."""
        if not self._responses:
            return ModelResponse(content="")
        response = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return ModelResponse(content=response, tool_calls=[])

    async def generate_structured(
        self,
        messages: list[Message],
        output_schema: type[Any],
    ) -> Any:
        """Attempt to instantiate the output schema with defaults."""
        try:
            return output_schema()
        except Exception:  # noqa: BLE001
            return {}
