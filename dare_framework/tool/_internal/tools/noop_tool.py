"""NoopTool implementation for testing.

A no-operation tool that always succeeds without any side effects.
"""

from __future__ import annotations

from typing import Any

from dare_framework.tool.kernel import ITool
from dare_framework.tool.types import (
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolResult,
    ToolType,
)


class NoopTool(ITool):
    """A no-operation tool for testing purposes.
    
    Always returns success with no side effects.
    """

    @property
    def name(self) -> str:
        return "noop"

    @property
    def description(self) -> str:
        return "A no-operation tool that does nothing and always succeeds."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
            },
        }

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "read_only"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 5

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(self, input: dict[str, Any], context: RunContext[Any]) -> ToolResult:
        """Execute the noop tool.
        
        Args:
            input: Input parameters (ignored).
            context: Run context.
            
        Returns:
            ToolResult indicating success.
        """
        return ToolResult(
            success=True,
            output={"status": "noop completed"},
        )


__all__ = ["NoopTool"]
