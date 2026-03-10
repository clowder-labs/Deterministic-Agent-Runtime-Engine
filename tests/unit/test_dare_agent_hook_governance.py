from __future__ import annotations

from typing import Any, Callable

import pytest

from dare_framework.agent.dare_agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Context, Message
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.infra.component import ComponentType
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan.types import ToolLoopRequest
from dare_framework.tool.types import ToolResult


class _RecordingModel:
    name = "recording-model"

    def __init__(self, responses: list[ModelResponse] | None = None) -> None:
        self._responses = list(responses or [ModelResponse(content="done", tool_calls=[])])
        self.inputs: list[ModelInput] = []

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = options
        self.inputs.append(model_input)
        if self._responses:
            return self._responses.pop(0)
        return ModelResponse(content="done", tool_calls=[])


class _RecordingToolGateway:
    def __init__(self) -> None:
        self.invoke_calls = 0

    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope, params)
        self.invoke_calls += 1
        return ToolResult(success=True, output={"ok": True})


class _PolicyHook:
    def __init__(self, resolver: Callable[[HookPhase, dict[str, Any]], HookResult]) -> None:
        self._resolver = resolver

    @property
    def name(self) -> str:
        return "policy-hook"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookResult:
        _ = args
        payload = kwargs.get("payload", {})
        return self._resolver(phase, payload if isinstance(payload, dict) else {})


def _build_agent(*, model: _RecordingModel, tool_gateway: _RecordingToolGateway, hook: _PolicyHook) -> DareAgent:
    return DareAgent(
        name="hook-governance-agent",
        model=model,
        context=Context(config=Config()),
        tool_gateway=tool_gateway,
        hooks=[hook],
    )


@pytest.mark.asyncio
async def test_before_tool_block_prevents_invoke() -> None:
    def resolver(phase: HookPhase, _payload: dict[str, Any]) -> HookResult:
        if phase is HookPhase.BEFORE_TOOL:
            return HookResult(decision=HookDecision.BLOCK)
        return HookResult(decision=HookDecision.ALLOW)

    model = _RecordingModel()
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(model=model, tool_gateway=tool_gateway, hook=_PolicyHook(resolver))

    result = await agent._run_tool_loop(  # noqa: SLF001 - intentional runtime-bridge unit test
        ToolLoopRequest(capability_id="tool.echo", params={"text": "hello"}),
        tool_name="echo",
        tool_call_id="tc-1",
    )

    assert result["success"] is False
    assert "hook policy" in str(result["error"])
    assert tool_gateway.invoke_calls == 0


@pytest.mark.asyncio
async def test_before_model_patch_replaces_model_input() -> None:
    patched_input = ModelInput(messages=[Message(role="user", text="patched-by-hook")], tools=[], metadata={})

    def resolver(phase: HookPhase, _payload: dict[str, Any]) -> HookResult:
        if phase is HookPhase.BEFORE_MODEL:
            return HookResult(
                decision=HookDecision.ALLOW,
                patch={"model_input": patched_input},
            )
        return HookResult(decision=HookDecision.ALLOW)

    model = _RecordingModel(responses=[ModelResponse(content="ok", tool_calls=[])])
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(model=model, tool_gateway=tool_gateway, hook=_PolicyHook(resolver))

    result = await agent._run_execute_loop(None)  # noqa: SLF001 - intentional runtime-bridge unit test

    assert result["success"] is True
    assert model.inputs
    assert model.inputs[0].messages[0].text == "patched-by-hook"


@pytest.mark.asyncio
async def test_before_context_assemble_patch_updates_model_metadata() -> None:
    def resolver(phase: HookPhase, _payload: dict[str, Any]) -> HookResult:
        if phase is HookPhase.BEFORE_CONTEXT_ASSEMBLE:
            return HookResult(
                decision=HookDecision.ALLOW,
                patch={"context_patch": {"metadata": {"governed": True}}},
            )
        return HookResult(decision=HookDecision.ALLOW)

    model = _RecordingModel(responses=[ModelResponse(content="ok", tool_calls=[])])
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(model=model, tool_gateway=tool_gateway, hook=_PolicyHook(resolver))

    result = await agent._run_execute_loop(None)  # noqa: SLF001 - intentional runtime-bridge unit test

    assert result["success"] is True
    assert model.inputs
    assert model.inputs[0].metadata.get("governed") is True


@pytest.mark.asyncio
async def test_after_model_payload_contains_model_output() -> None:
    observed_payloads: list[dict[str, Any]] = []

    def resolver(phase: HookPhase, payload: dict[str, Any]) -> HookResult:
        if phase is HookPhase.AFTER_MODEL:
            observed_payloads.append(payload)
        return HookResult(decision=HookDecision.ALLOW)

    response = ModelResponse(
        content="assistant response",
        tool_calls=[{"id": "c1", "name": "read_file", "arguments": {"path": "README.md"}}],
        usage={"prompt_tokens": 2, "completion_tokens": 4, "total_tokens": 6},
    )
    model = _RecordingModel(responses=[response])
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(model=model, tool_gateway=tool_gateway, hook=_PolicyHook(resolver))

    result = await agent._run_execute_loop(None)  # noqa: SLF001 - intentional runtime-bridge unit test

    assert result["success"] is True
    assert observed_payloads
    model_output = observed_payloads[0].get("model_output")
    assert isinstance(model_output, dict)
    assert model_output.get("content") == "assistant response"
    assert model_output.get("tool_calls") == [
        {"id": "c1", "name": "read_file", "arguments": {"path": "README.md"}}
    ]


@pytest.mark.asyncio
async def test_model_hook_payload_contains_conversation_id_from_task_metadata() -> None:
    observed_payloads: list[dict[str, Any]] = []

    def resolver(phase: HookPhase, payload: dict[str, Any]) -> HookResult:
        if phase is HookPhase.BEFORE_MODEL:
            observed_payloads.append(payload)
        return HookResult(decision=HookDecision.ALLOW)

    model = _RecordingModel(responses=[ModelResponse(content="ok", tool_calls=[])])
    tool_gateway = _RecordingToolGateway()
    agent = _build_agent(model=model, tool_gateway=tool_gateway, hook=_PolicyHook(resolver))

    await agent(Message(role="user", text="hello", metadata={"conversation_id": "session-42"}))

    assert observed_payloads
    assert observed_payloads[0].get("conversation_id") == "session-42"
