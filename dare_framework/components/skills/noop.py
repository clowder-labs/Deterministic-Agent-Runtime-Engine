from __future__ import annotations

from typing import Any

from dare_framework.components.base_component import ConfigurableComponent
from dare_framework.contracts.run_context import RunContext
from dare_framework.contracts.tool import ToolResult
from dare_framework.contracts import ComponentType

from .protocols import ISkill


class NoOpSkill(ConfigurableComponent, ISkill):
    """A minimal skill implementation used as a placeholder."""

    component_type = ComponentType.SKILL
    name = "noop"

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        return ToolResult(success=True, output={"result": "noop"})
