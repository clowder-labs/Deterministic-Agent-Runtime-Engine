"""NoopTool implementation for testing.

A no-operation tool that always succeeds without any side effects.
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
    ) -> ToolResult[NoopOutput]:
        """Execute the noop tool.

        Args:
            run_context: Runtime invocation context.

        Returns:
            Success payload for no-op completion.
        """
        _ = run_context
        return ToolResult(
            success=True,
            output={"status": "noop completed"},
        )


class NoopOutput(TypedDict):
    status: str


__all__ = ["NoopTool"]
