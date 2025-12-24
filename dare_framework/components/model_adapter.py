from __future__ import annotations

from typing import Iterable

from ..core.interfaces import IModelAdapter
from .base_component import BaseComponent
from ..core.models import Message, ModelResponse


class MockModelAdapter(BaseComponent, IModelAdapter):
    def __init__(self, responses: Iterable[str] | None = None):
        self._responses = list(responses or ["ok"])
        self._index = 0

    async def generate(self, messages: list[Message], tools=None, options=None) -> ModelResponse:
        if not self._responses:
            return ModelResponse(content="")
        response = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return ModelResponse(content=response, tool_calls=[])

    async def generate_structured(self, messages: list[Message], output_schema: type) -> object:
        try:
            return output_schema()
        except Exception:  # noqa: BLE001
            return {}
