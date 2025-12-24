import pytest

from dare_framework.component_manager import (
    ENTRYPOINT_MODEL_ADAPTERS,
    ENTRYPOINT_TOOLS,
    ENTRYPOINT_VALIDATORS,
    ModelAdapterManager,
    ToolManager,
    ValidatorManager,
)
from dare_framework.components.base_component import BaseComponent
from dare_framework.components.registries import ToolRegistry
from dare_framework.core.interfaces import IModelAdapter, ITool, IValidator
from dare_framework.core.models import (
    Milestone,
    ModelResponse,
    ProposedStep,
    RunContext,
    ToolRiskLevel,
    ToolType,
    ValidationResult,
    VerifyResult,
)


class FakeEntryPoint:
    def __init__(self, name, loader):
        self.name = name
        self._loader = loader

    def load(self):
        return self._loader


class FakeEntryPoints:
    def __init__(self, mapping):
        self._mapping = mapping

    def select(self, group=None):
        return list(self._mapping.get(group, []))


class RecordingValidator(BaseComponent, IValidator):
    def __init__(self, name: str, order: int, log: list[str]):
        self._name = name
        self._order = order
        self._log = log

    @property
    def order(self) -> int:
        return self._order

    async def init(self, config=None, prompts=None) -> None:
        self._log.append(f"init:{self._name}")

    def register(self, registrar) -> None:
        self._log.append(f"register:{self._name}")
        registrar.register_component(self)

    async def validate_plan(self, proposed_steps: list[ProposedStep], ctx: RunContext) -> ValidationResult:
        return ValidationResult(success=True, errors=[])

    async def validate_milestone(self, milestone: Milestone, result, ctx: RunContext) -> VerifyResult:
        return VerifyResult(success=True, errors=[], evidence=[])

    async def validate_evidence(self, evidence, predicate) -> bool:
        return True


class DummyTool(BaseComponent, ITool):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def description(self) -> str:
        return "dummy tool"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    @property
    def output_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    @property
    def tool_type(self):
        return ToolType.ATOMIC

    @property
    def risk_level(self):
        return ToolRiskLevel.READ_ONLY

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 1

    @property
    def produces_assertions(self) -> list[dict]:
        return []

    @property
    def is_work_unit(self) -> bool:
        return False

    async def execute(self, input: dict, context: RunContext):
        raise RuntimeError("Not implemented")


class DummyModelAdapter(BaseComponent, IModelAdapter):
    async def generate(self, messages, tools=None, options=None) -> ModelResponse:
        return ModelResponse(content="ok", tool_calls=[])

    async def generate_structured(self, messages, output_schema):
        return output_schema()


@pytest.mark.asyncio
async def test_validator_manager_orders_components():
    log: list[str] = []

    def low_factory():
        return RecordingValidator("low", 10, log)

    def high_factory():
        return RecordingValidator("high", 50, log)

    entry_points = FakeEntryPoints(
        {
            ENTRYPOINT_VALIDATORS: [
                FakeEntryPoint("low", low_factory),
                FakeEntryPoint("high", high_factory),
            ]
        }
    )
    manager = ValidatorManager(entry_points_loader=lambda: entry_points)

    await manager.load(None)

    assert log == ["init:low", "register:low", "init:high", "register:high"]


@pytest.mark.asyncio
async def test_tool_manager_registers_tools():
    registry = ToolRegistry()
    entry_points = FakeEntryPoints({ENTRYPOINT_TOOLS: [FakeEntryPoint("dummy", DummyTool)]})
    manager = ToolManager(registry, entry_points_loader=lambda: entry_points)

    await manager.load(None)

    assert registry.get_tool("dummy") is not None


@pytest.mark.asyncio
async def test_model_adapter_manager_returns_ordered_list():
    entry_points = FakeEntryPoints({ENTRYPOINT_MODEL_ADAPTERS: [FakeEntryPoint("adapter", DummyModelAdapter)]})
    manager = ModelAdapterManager(entry_points_loader=lambda: entry_points)

    adapters = await manager.load(None)

    assert len(adapters) == 1
    assert isinstance(adapters[0], DummyModelAdapter)
