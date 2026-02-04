from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent
from dare_framework.config.types import ComponentConfig, Config
from dare_framework.hook.kernel import IHook
from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan.interfaces import IValidator
from dare_framework.plan.types import ProposedPlan
from dare_framework.tool.default_tool_manager import ToolManager
from dare_framework.tool.kernel import ITool
from dare_framework.tool.types import ToolResult


class DummyModelAdapter(IModelAdapter):
    def __init__(self, content: str) -> None:
        self._content = content

    @property
    def name(self) -> str:
        return "dummy_model_adapter"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.MODEL_ADAPTER

    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        return ModelResponse(content=self._content)


class FixedModelAdapterManager:
    def __init__(self, adapter: IModelAdapter) -> None:
        self._adapter = adapter

    def load_model_adapter(self, *, config: Config | None = None) -> IModelAdapter | None:
        return self._adapter


class DummyTool(ITool):
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.TOOL

    async def execute(self, input: dict[str, Any], context: Any) -> ToolResult:
        return ToolResult(success=True, output=input)


class RecordingValidator:
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self._calls = calls

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.VALIDATOR

    async def validate_plan(self, plan: Any, ctx: Any) -> Any:
        self._calls.append(self.name)
        from dare_framework.plan.types import ValidatedPlan

        return ValidatedPlan(success=True, plan_description=plan.plan_description)

    async def verify_milestone(self, result: Any, ctx: Any) -> Any:
        from dare_framework.plan.types import VerifyResult

        return VerifyResult(success=True)


class FixedValidatorManager:
    def __init__(self, validators: list[IValidator]) -> None:
        self._validators = list(validators)

    def load_validators(self, *, config: Config | None = None) -> list[IValidator]:
        return list(self._validators)


class RecordingHook:
    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: Any, *args: Any, **kwargs: Any) -> None:
        return None


class FixedHookManager:
    def __init__(self, hooks: list[IHook]) -> None:
        self._hooks = list(hooks)

    def load_hooks(self, *, config: Config | None = None) -> list[IHook]:
        return list(self._hooks)


@pytest.mark.asyncio
async def test_simple_chat_builder_resolves_model_via_manager() -> None:
    manager_model = DummyModelAdapter("from-manager")
    agent = (
        BaseAgent.simple_chat_agent_builder("test")
        .with_managers(model_adapter_manager=FixedModelAdapterManager(manager_model))
        .build()
    )

    result = await agent.run("hello")
    assert result.output == "from-manager"


@pytest.mark.asyncio
async def test_simple_chat_builder_explicit_model_overrides_manager() -> None:
    explicit = DummyModelAdapter("explicit")
    manager_model = DummyModelAdapter("from-manager")
    agent = (
        BaseAgent.simple_chat_agent_builder("test")
        .with_model(explicit)
        .with_managers(model_adapter_manager=FixedModelAdapterManager(manager_model))
        .build()
    )

    result = await agent.run("hello")
    assert result.output == "explicit"


def test_simple_chat_builder_tools_extend_and_config_boundary() -> None:
    explicit_tool = DummyTool("explicit_tool")
    enabled_tool = DummyTool("enabled_tool")
    disabled_tool = DummyTool("disabled_tool")

    config = Config(
        components={
            ComponentType.TOOL.value: ComponentConfig(
                disabled=[
                    "disabled_tool",
                    "explicit_tool",  # MUST NOT remove explicitly injected components.
                ]
            )
        }
    )
    agent = (
        BaseAgent.simple_chat_agent_builder("test")
        .with_model(DummyModelAdapter("ok"))
        .with_config(config)
        .with_tool_gateway(_build_tool_manager([enabled_tool, disabled_tool]))
        .add_tools(explicit_tool)
        .build()
    )

    tool_defs = agent.context.listing_tools()
    names = {tool_def.get("metadata", {}).get("display_name") for tool_def in tool_defs}
    assert "explicit_tool" in names
    assert "enabled_tool" in names
    assert "disabled_tool" not in names


def _build_tool_manager(tools: list[ITool]) -> ToolManager:
    manager = ToolManager()
    for tool in tools:
        manager.register_tool(tool)
    return manager


@pytest.mark.asyncio
async def test_five_layer_builder_validators_extend_and_config_boundary() -> None:
    calls: list[str] = []
    explicit_validator = RecordingValidator("explicit_validator", calls)
    enabled_validator = RecordingValidator("enabled_manager_validator", calls)
    disabled_validator = RecordingValidator("disabled_manager_validator", calls)

    config = Config(
        components={
            ComponentType.VALIDATOR.value: ComponentConfig(
                disabled=[
                    "disabled_manager_validator",
                    "explicit_validator",  # MUST NOT remove explicitly injected components.
                ]
            )
        }
    )
    agent = (
        BaseAgent.dare_agent_builder("test")
        .with_model(DummyModelAdapter("ok"))
        .with_config(config)
        .with_managers(validator_manager=FixedValidatorManager([enabled_validator, disabled_validator]))
        .add_validators(explicit_validator)
        .build()
    )

    validator = getattr(agent, "_validator", None)
    assert validator is not None

    await validator.validate_plan(ProposedPlan(plan_description="p"), agent.context)
    assert calls == ["explicit_validator", "enabled_manager_validator"]


def test_five_layer_builder_hooks_extend_and_config_boundary() -> None:
    explicit_hook = RecordingHook("explicit_hook")
    enabled_hook = RecordingHook("enabled_manager_hook")
    disabled_hook = RecordingHook("disabled_manager_hook")

    config = Config(
        components={
            ComponentType.HOOK.value: ComponentConfig(
                disabled=[
                    "disabled_manager_hook",
                    "explicit_hook",  # MUST NOT remove explicitly injected components.
                ]
            )
        }
    )
    agent = (
        BaseAgent.dare_agent_builder("test")
        .with_model(DummyModelAdapter("ok"))
        .with_config(config)
        .with_managers(hook_manager=FixedHookManager([enabled_hook, disabled_hook]))
        .add_hooks(explicit_hook)
        .build()
    )

    hooks = getattr(agent, "_hooks", [])
    names = {hook.name for hook in hooks}
    assert "explicit_hook" in names
    assert "enabled_manager_hook" in names
    assert "disabled_manager_hook" not in names
