"""EchoTool implementation for testing.

A tool that echoes back the input message.
"""

from __future__ import annotations

from typing import Any, TypedDict

from dare_framework.tool.kernel import ITool
from dare_framework.tool._internal.util.__tool_schema_util import (
    infer_input_schema_from_execute,
    infer_output_schema_from_execute,
)
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
        return infer_input_schema_from_execute(type(self).execute)

    @property
    def output_schema(self) -> dict[str, Any]:
        return infer_output_schema_from_execute(type(self).execute) or {}

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

    # noinspection PyMethodOverriding
    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        message: str,
    ) -> ToolResult[EchoOutput]:
        """Execute the echo tool.

        Args:
            run_context: Runtime invocation context.
            message: The message to echo back.

        Returns:
            Echo payload containing the same message.
        """
        _ = run_context
        return ToolResult(
            success=True,
            output={"echo": message},
        )


class EchoOutput(TypedDict):
    echo: str


__all__ = ["EchoTool"]
