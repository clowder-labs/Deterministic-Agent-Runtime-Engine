from __future__ import annotations

from ..core.models import Evidence, RunContext, ToolResult, ToolRiskLevel, ToolType, new_id


class NoOpTool:
    @property
    def name(self) -> str:
        return "noop"

    @property
    def description(self) -> str:
        return "No-op tool for default runtime wiring."

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    @property
    def output_schema(self) -> dict:
        return {"type": "object", "properties": {"status": {"type": "string"}}}

    @property
    def risk_level(self):
        return ToolRiskLevel.READ_ONLY

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
    def produces_assertions(self) -> list[dict]:
        return []

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(self, input: dict, context: RunContext) -> ToolResult:
        return ToolResult(
            success=True,
            output={"status": "ok"},
            evidence=[Evidence(evidence_id=new_id("evidence"), kind="noop", payload={"status": "ok"})],
        )
