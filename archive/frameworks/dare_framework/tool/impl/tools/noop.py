from __future__ import annotations

from dare_framework.contracts.evidence import Evidence
from dare_framework.contracts.ids import generator_id
from dare_framework.contracts.risk import RiskLevel
from dare_framework.contracts.run_context import RunContext
from dare_framework.contracts.tool import ToolResult, ToolType
from dare_framework.contracts import ComponentType
from dare_framework.builder.base_component import ConfigurableComponent


class NoOpTool(ConfigurableComponent):
    component_type = ComponentType.TOOL

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
    def produces_assertions(self) -> list[dict]:
        return []

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(self, input: dict, context: RunContext) -> ToolResult:
        return ToolResult(
            success=True,
            output={"status": "ok"},
            evidence=[Evidence(evidence_id=generator_id("evidence"), kind="noop", payload={"status": "ok"})],
        )
