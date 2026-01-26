"""No-op skill implementation."""

from __future__ import annotations

from typing import Any

from dare_framework.tool.interfaces import ISkill
from dare_framework.tool.types import RunContext, ToolResult


class NoOpSkill(ISkill):
    """A minimal skill implementation used as a placeholder."""

    @property
    def name(self) -> str:
        return "noop"

    @property
    def description(self) -> str:
        return "No-op skill placeholder."

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        return ToolResult(success=True, output={"result": "noop"})
