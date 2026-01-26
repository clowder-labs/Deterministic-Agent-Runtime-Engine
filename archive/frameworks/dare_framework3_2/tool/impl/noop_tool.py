"""No-op tool implementation."""

from __future__ import annotations

from typing import Any

from dare_framework3_2.tool.component import ITool
from dare_framework3_2.tool.types import (
    Evidence,
    RiskLevel,
    RunContext,
    ToolResult,
    ToolType,
)
from dare_framework3_2.utils.ids import generate_id


class NoOpTool(ITool):
    """A no-op tool for default runtime wiring.
    
    Useful as a safe default when no tools are configured,
    or for testing scenarios.
    """

    @property
    def name(self) -> str:
        return "noop"

    @property
    def description(self) -> str:
        return "No-op tool for default runtime wiring."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    @property
    def output_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"status": {"type": "string"}}}

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.READ_ONLY

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 5

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        return []

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Always succeeds with status 'ok'."""
        return ToolResult(
            success=True,
            output={"status": "ok"},
            evidence=[
                Evidence(
                    evidence_id=generate_id("evidence"),
                    kind="noop",
                    payload={"status": "ok"},
                )
            ],
        )
