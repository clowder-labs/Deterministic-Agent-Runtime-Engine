from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent, DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
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
        return ToolResult(success=False, output={}, error="unexpected invoke")


class _RecordingChannel:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> Any:
        raise RuntimeError("not used")

    async def send(self, msg: Any) -> None:
        self.sent.append(msg)

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> Any:
        return None

    def get_agent_control_handler(self) -> Any:
        return None


@pytest.mark.asyncio
async def test_dare_agent_does_not_emit_hook_messages_without_transport_hook() -> None:
    transport = _RecordingChannel()
    agent = DareAgent(
        name="hook-boundary",
        model=_Model(),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
    )

    await agent("hello", transport=transport)

    hook_payloads = [
        envelope.payload
        for envelope in transport.sent
        if isinstance(envelope.payload, dict) and envelope.payload.get("type") == "hook"
    ]
    assert hook_payloads == []


@pytest.mark.asyncio
async def test_dare_builder_registers_agent_event_transport_hook_when_channel_present() -> None:
    channel = _RecordingChannel()
    builder = BaseAgent.dare_agent_builder("hook-builder").with_model(_Model())

    agent = builder._build_impl(
        config=Config(),
        model=_Model(),
        context=Context(config=Config()),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=channel,
    )

    hooks = getattr(agent, "_hooks", [])
    names = {hook.name for hook in hooks}
    assert "agent_event_transport" in names
