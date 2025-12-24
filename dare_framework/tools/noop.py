from __future__ import annotations

from dataclasses import dataclass

from dare_framework.components.interfaces import ITool
from dare_framework.core.models import RiskLevel, RunContext, ToolResult, ToolType


@dataclass
class NoopTool(ITool):
    name: str = "noop"
    description: str = "No-op tool for default plans."
    tool_type: ToolType = ToolType.ATOMIC
    risk_level: RiskLevel = RiskLevel.READ_ONLY

    def get_input_schema(self) -> dict:
        return {"type": "object", "properties": {"message": {"type": "string"}}}

    async def execute(self, input: dict, ctx: RunContext) -> ToolResult:
        message = input.get("message", "")
        return ToolResult(success=True, output=f"noop:{message}")
