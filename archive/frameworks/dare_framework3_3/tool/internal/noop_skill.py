"""No-op skill implementation."""

from __future__ import annotations

from typing import Any

from dare_framework3_3.tool.component import ISkill
from dare_framework3_3.tool.types import RunContext, ToolResult


class NoOpSkill(ISkill):
    """A minimal skill implementation used as a placeholder."""

    @property
    def name(self) -> str:
        return "noop"

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Always succeeds with result 'noop'."""
        return ToolResult(success=True, output={"result": "noop"})
