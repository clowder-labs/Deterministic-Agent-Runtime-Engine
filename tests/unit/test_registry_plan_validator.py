from __future__ import annotations

from typing import Any

import pytest

from dare_framework.plan._internal.registry_validator import RegistryPlanValidator
from dare_framework.plan.types import Envelope, ProposedPlan, ProposedStep
from dare_framework.security.types import RiskLevel
from dare_framework.tool._internal.managers.tool_manager import ToolManager
from dare_framework.tool.interfaces import ITool
from dare_framework.tool.types import CapabilityKind, ToolResult, ToolType
from dare_framework.infra.component import ComponentType


class DummyTool(ITool):
    def __init__(self, name: str, *, risk_level: str = "read_only") -> None:
        self._name = name
        self._risk_level = risk_level

    @property
    def name(self) -> str:
        return self._name

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TOOL

    @property
    def description(self) -> str:
        return "dummy"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return None

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> str:
        return self._risk_level

    @property
    def requires_approval(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 30

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(self, input: dict[str, Any], context: Any) -> ToolResult:
        return ToolResult(success=True, output=input)


@pytest.mark.asyncio
async def test_registry_validator_derives_trusted_metadata() -> None:
    tool = DummyTool("write_file", risk_level="idempotent_write")
    manager = ToolManager()
    descriptor = manager.register_tool(tool)
    validator = RegistryPlanValidator(tool_manager=manager)

    plan = ProposedPlan(
        plan_description="plan",
        steps=[
            ProposedStep(
                step_id="s1",
                capability_id=descriptor.id,
                params={"path": "x"},
                envelope=Envelope(risk_level=RiskLevel.NON_IDEMPOTENT_EFFECT),
            )
        ],
    )

    validated = await validator.validate_plan(plan, {})

    assert validated.success is True
    assert validated.steps[0].risk_level == RiskLevel.IDEMPOTENT_WRITE
    assert validated.steps[0].metadata["capability_kind"] == CapabilityKind.TOOL.value
    assert validated.steps[0].envelope is not None
    assert validated.steps[0].envelope.risk_level == RiskLevel.IDEMPOTENT_WRITE


@pytest.mark.asyncio
async def test_registry_validator_flags_unknown_capability() -> None:
    validator = RegistryPlanValidator(tool_manager=ToolManager())

    plan = ProposedPlan(
        plan_description="plan",
        steps=[
            ProposedStep(
                step_id="s1",
                capability_id="tool:missing",
                params={},
            )
        ],
    )

    validated = await validator.validate_plan(plan, {})

    assert validated.success is False
    assert "unknown capability" in validated.errors[0]


@pytest.mark.asyncio
async def test_registry_validator_handles_plan_tool_prefix() -> None:
    validator = RegistryPlanValidator(tool_manager=ToolManager())

    plan = ProposedPlan(
        plan_description="plan",
        steps=[
            ProposedStep(
                step_id="s1",
                capability_id="plan:replan",
                params={},
            )
        ],
    )

    validated = await validator.validate_plan(plan, {})

    assert validated.success is True
    assert validated.steps[0].risk_level == RiskLevel.READ_ONLY
    assert validated.steps[0].metadata["capability_kind"] == CapabilityKind.PLAN_TOOL.value
