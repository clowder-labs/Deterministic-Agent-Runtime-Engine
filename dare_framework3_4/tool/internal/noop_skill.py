"""No-op skill implementation."""

from __future__ import annotations

from typing import Any

from dare_framework3_4.tool.component import ISkill
from dare_framework3_4.tool.types import RunContext, ToolResult


class NoOpSkill(ISkill):
    """A minimal skill implementation used as a placeholder."""

    @property
    def name(self) -> str:
        return "noop"

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        return ToolResult(success=True, output={"result": "noop"})
