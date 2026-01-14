import pytest

from dare_framework.components.composite_tool import CompositeTool
from dare_framework.components.registries import ToolRegistry
from dare_framework.core.interfaces import ITool
from dare_framework.core.models import RunContext, ToolResult, ToolRiskLevel, ToolType


class GoodTool(ITool):
    order = 10

    @property
    def name(self) -> str:
        return "good"

    @property
    def description(self) -> str:
        return "good tool"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {"x": {"type": "integer"}}}

    @property
    def output_schema(self) -> dict:
        return {"type": "object", "properties": {"value": {"type": "integer"}}}

    @property
    def risk_level(self):
        return ToolRiskLevel.READ_ONLY

    @property
    def tool_type(self):
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
        return ToolResult(success=True, output={"value": input.get("x")}, error=None, evidence=[])

    async def init(self, config=None, prompts=None) -> None:
        return None

    def register(self, registrar) -> None:
        return None

    async def close(self) -> None:
        return None


class FailTool(GoodTool):
    @property
    def name(self) -> str:
        return "fail"

    async def execute(self, input: dict, context: RunContext) -> ToolResult:
        return ToolResult(success=False, output={}, error="boom", evidence=[])


@pytest.mark.asyncio
async def test_composite_tool_runs_steps():
    registry = ToolRegistry()
    registry.register_tool(GoodTool())
    composite = CompositeTool(
        name="combo",
        description="",
        steps=[{"tool": "good", "input": {"x": 1}}],
        toolkit=registry,
    )

    result = await composite.execute({}, RunContext(deps=None, run_id="run"))

    assert result.success is True
    assert result.output["steps"][0]["output"]["value"] == 1
    assert any(ev.kind == "composite_tool" for ev in result.evidence)


@pytest.mark.asyncio
async def test_composite_tool_errors_on_missing_tool():
    registry = ToolRegistry()
    registry.register_tool(GoodTool())
    composite = CompositeTool(
        name="combo",
        description="",
        steps=[{"tool": "missing"}],
        toolkit=registry,
    )

    result = await composite.execute({}, RunContext(deps=None, run_id="run"))

    assert result.success is False
    assert "missing" in (result.error or "")
