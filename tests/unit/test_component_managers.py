import pytest

pytest.skip(
    "Legacy component manager tests rely on archived plugin system; "
    "port to canonical dare_framework once manager/entrypoint APIs exist.",
    allow_module_level=True,
)

from dare_framework.builder.base_component import ConfigurableComponent
from dare_framework.config import Config
from dare_framework.model.components import IModelAdapter
from dare_framework.model.types import ModelResponse
from dare_framework.contracts.risk import RiskLevel
from dare_framework.contracts.run_context import RunContext
from dare_framework.contracts.tool import ITool, ToolResult, ToolType
from dare_framework.contracts import ComponentType
from dare_framework.builder.plugin_system.entrypoint_managers import (
    EntrypointModelAdapterManager,
    EntrypointToolManager,
    EntrypointValidatorManager,
)
from dare_framework.builder.plugin_system.entrypoints import (
    ENTRYPOINT_V2_MODEL_ADAPTERS,
    ENTRYPOINT_V2_TOOLS,
    ENTRYPOINT_V2_VALIDATORS,
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


class RecordingValidator(ConfigurableComponent):
    component_type = ComponentType.VALIDATOR

    def __init__(self, name: str, order: int, log: list[str]):
        self._name = name
        self._order = order
        self._log = log

    @property
    def name(self) -> str:
        return self._name

    @property
    def order(self) -> int:
        return self._order

    async def init(self, config=None, prompts=None) -> None:
        self._log.append(f"init:{self._name}")

    def register(self, registrar) -> None:
        self._log.append(f"register:{self._name}")


class DummyTool(ConfigurableComponent, ITool):
    component_type = ComponentType.TOOL

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
        return RiskLevel.READ_ONLY

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
        return ToolResult(success=True, output={"ok": True}, error=None, evidence=[])


class DummyModelAdapter(ConfigurableComponent, IModelAdapter):
    component_type = ComponentType.MODEL_ADAPTER
    name = "dummy"

    async def generate(self, messages, tools=None, options=None) -> ModelResponse:
        return ModelResponse(content="ok", tool_calls=[])

    async def generate_structured(self, messages, output_schema):
        return output_schema()


def test_entrypoint_validator_manager_orders_components():
    log: list[str] = []

    def low_factory():
        return RecordingValidator("low", 10, log)

    def high_factory():
        return RecordingValidator("high", 50, log)

    entry_points = FakeEntryPoints(
        {
            ENTRYPOINT_V2_VALIDATORS: [
                FakeEntryPoint("low", low_factory),
                FakeEntryPoint("high", high_factory),
            ]
        }
    )
    manager = EntrypointValidatorManager(entry_points_loader=lambda: entry_points)
    validators = manager.load_validators(config=None)

    assert [getattr(v, "name", None) for v in validators] == ["low", "high"]


def test_entrypoint_tool_manager_filters_and_orders_tools():
    class ToolA(DummyTool):
        @property
        def name(self) -> str:
            return "a"

        @property
        def order(self) -> int:
            return 20

    class ToolB(DummyTool):
        @property
        def name(self) -> str:
            return "b"

        @property
        def order(self) -> int:
            return 10

    class DisabledTool(DummyTool):
        @property
        def name(self) -> str:
            return "disabled"

    entry_points = FakeEntryPoints(
        {ENTRYPOINT_V2_TOOLS: [FakeEntryPoint("a", ToolA), FakeEntryPoint("b", ToolB), FakeEntryPoint("x", DisabledTool)]}
    )
    manager = EntrypointToolManager(entry_points_loader=lambda: entry_points)
    config = Config.from_dict({"components": {"tool": {"disabled": ["disabled"]}}})

    tools = manager.load_tools(config=config)
    assert [tool.name for tool in tools] == ["b", "a"]


def test_entrypoint_model_adapter_manager_selects_by_config():
    class MockAdapter(DummyModelAdapter):
        name = "mock"

    class OtherAdapter(DummyModelAdapter):
        name = "other"

    entry_points = FakeEntryPoints(
        {
            ENTRYPOINT_V2_MODEL_ADAPTERS: [
                FakeEntryPoint("mock", MockAdapter),
                FakeEntryPoint("other", OtherAdapter),
            ]
        }
    )
    manager = EntrypointModelAdapterManager(entry_points_loader=lambda: entry_points)
    config = Config.from_dict({"llm": {"adapter": "mock"}})

    adapter = manager.load_model_adapter(config=config)
    assert adapter is not None
    assert getattr(adapter, "name", None) == "mock"


def test_entrypoint_model_adapter_manager_missing_name_returns_none():
    entry_points = FakeEntryPoints({ENTRYPOINT_V2_MODEL_ADAPTERS: [FakeEntryPoint("dummy", DummyModelAdapter)]})
    manager = EntrypointModelAdapterManager(entry_points_loader=lambda: entry_points)
    config = Config.from_dict({"llm": {"model": "m1"}})

    assert manager.load_model_adapter(config=config) is None


def test_entrypoint_model_adapter_manager_missing_entrypoint_raises():
    manager = EntrypointModelAdapterManager(entry_points_loader=lambda: FakeEntryPoints({}))
    config = Config.from_dict({"llm": {"adapter": "missing"}})
    with pytest.raises(KeyError):
        manager.load_model_adapter(config=config)


def test_entrypoint_model_adapter_manager_rejects_disabled_adapter():
    class MockAdapter(DummyModelAdapter):
        name = "mock"

    entry_points = FakeEntryPoints({ENTRYPOINT_V2_MODEL_ADAPTERS: [FakeEntryPoint("mock", MockAdapter)]})
    manager = EntrypointModelAdapterManager(entry_points_loader=lambda: entry_points)
    config = Config.from_dict({"llm": {"adapter": "mock"}, "components": {"model_adapter": {"disabled": ["mock"]}}})
    with pytest.raises(RuntimeError):
        manager.load_model_adapter(config=config)
