from __future__ import annotations

from typing import Any

from dare_framework.components.base_component import ConfigurableComponent
from dare_framework.core.budget.models import Budget
from dare_framework.contracts import ComponentType
from dare_framework.contracts.memory import IMemory


class NoOpMemory(ConfigurableComponent, IMemory):
    """A memory implementation that always returns empty results."""

    component_type = ComponentType.MEMORY
    name = "noop"

    async def retrieve(self, query: str, *, budget: Budget | None = None) -> list[dict[str, Any]]:
        return []

    async def add(self, items: list[dict[str, Any]]) -> None:
        return None
