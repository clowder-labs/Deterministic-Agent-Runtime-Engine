from __future__ import annotations

from typing import Any

from dare_framework.agent import BaseAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.hook.interfaces import IHookManager
from dare_framework.hook.types import HookPhase
from dare_framework.infra.component import ComponentType
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.tool.types import ToolResult


class _Model:
    name = "mock-model"

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        return ModelResponse(content="ok", tool_calls=[])


class _ToolGateway:
    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope, params)
        return ToolResult(success=True, output={})


class _Hook:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> None:
        _ = (phase, args, kwargs)
        return None


class _HookManagerImpl(IHookManager):
    def __init__(self, hooks: list[_Hook]) -> None:
        self._hooks = hooks

    def load_hooks(self, *, config: Config | None = None) -> list[_Hook]:
        _ = config
        return list(self._hooks)


class _RecordingChannel:
    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> Any:
        return None

    async def send(self, msg: Any) -> None:
        _ = msg

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> Any:
        return None

    def get_agent_control_handler(self) -> Any:
        return None


def test_builder_orders_hooks_by_source_and_config_priority() -> None:
    config = Config.from_dict(
        {
            "hooks": {
                "version": 1,
                "defaults": {"priority": 100},
                "entries": [
                    {"name": "config_a", "priority": 10},
                    {"name": "config_b", "priority": 50},
                ],
            }
        }
    )
    manager = _HookManagerImpl([_Hook("config_b"), _Hook("config_a")])
    builder = (
        BaseAgent.dare_agent_builder("ordered-hooks")
        .with_managers(hook_manager=manager)
        .add_hooks(_Hook("code_hook"))
    )

    agent = builder._build_impl(
        config=config,
        model=_Model(),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=_RecordingChannel(),
    )

    hook_names = [hook.name for hook in getattr(agent, "_hooks", [])]
    assert hook_names == ["agent_event_transport", "config_a", "config_b", "code_hook"]


def test_builder_auto_injects_llm_io_capture_hook_when_capture_enabled(tmp_path) -> None:
    config = Config.from_dict(
        {
            "workspace_dir": str(tmp_path),
            "observability": {
                "capture_content": True,
            },
        }
    )
    builder = BaseAgent.dare_agent_builder("capture-hooks")

    agent = builder._build_impl(
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    hook_names = [hook.name for hook in getattr(agent, "_hooks", [])]
    assert "llm_io_capture" in hook_names
