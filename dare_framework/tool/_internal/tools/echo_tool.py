"""EchoTool implementation for testing.

A tool that echoes back the input message.
"""

from __future__ import annotations

from typing import Any

from dare_framework.tool.interfaces import ITool
from dare_framework.tool.types import (
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolResult,
    ToolType,
)


class EchoTool(ITool):
    """A tool that echoes back the input message.
    
    Useful for testing and demonstrating tool invocation.
    """

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes back the input message."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to echo back.",
                },
            },
            "required": ["message"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "echo": {"type": "string"},
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
        """Execute the echo tool.
        
        Args:
            input: Input parameters containing 'message'.
            context: Run context.
            
        Returns:
            ToolResult with echoed message.
        """
        message = input.get("message", "")
        return ToolResult(
            success=True,
            output={"echo": message},
        )


__all__ = ["EchoTool"]
