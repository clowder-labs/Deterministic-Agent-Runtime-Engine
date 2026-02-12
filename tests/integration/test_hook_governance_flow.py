from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent.dare_agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.hook._internal.legacy_adapter import LegacyHookAdapter
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.infra.component import ComponentType
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.tool.types import ToolResult


class _SequenceModel:
    name = "sequence-model"

    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
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
        return ToolResult(success=True, output={"capability_id": capability_id})


class _GovernanceHook:
    def __init__(self, decision: HookDecision) -> None:
        self._decision = decision

    @property
    def name(self) -> str:
        return f"hook-{self._decision.value}"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookResult:
        _ = (args, kwargs)
        if phase is HookPhase.BEFORE_TOOL:
            return HookResult(decision=self._decision)
        return HookResult(decision=HookDecision.ALLOW)


class _LegacyAllowHook:
    @property
    def name(self) -> str:
        return "legacy-allow"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> dict[str, Any]:
        _ = (phase, args, kwargs)
        return {"legacy": True}


def _agent_with_single_tool_call(*, hooks: list[Any], tool_gateway: _RecordingToolGateway) -> DareAgent:
    model = _SequenceModel(
        responses=[
            ModelResponse(
                content="",
                tool_calls=[{"id": "tc-1", "name": "echo", "capability_id": "tool.echo", "arguments": {"text": "hi"}}],
            ),
            ModelResponse(content="done", tool_calls=[]),
        ]
    )
    return DareAgent(
        name="hook-governance-flow",
        model=model,
        context=Context(config=Config()),
        tool_gateway=tool_gateway,
        hooks=hooks,
    )


@pytest.mark.asyncio
async def test_governance_block_prevents_tool_execution() -> None:
    gateway = _RecordingToolGateway()
    agent = _agent_with_single_tool_call(
        hooks=[_GovernanceHook(HookDecision.BLOCK)],
        tool_gateway=gateway,
    )

    result = await agent("blocked flow")

    assert gateway.invoke_calls == 0
    assert result.success is True
    tool_messages = [msg for msg in agent.context.stm_get() if msg.role == "tool"]
    assert tool_messages
    assert "hook policy" in tool_messages[0].content


@pytest.mark.asyncio
async def test_governance_ask_prevents_tool_execution_without_approval_bridge() -> None:
    gateway = _RecordingToolGateway()
    agent = _agent_with_single_tool_call(
        hooks=[_GovernanceHook(HookDecision.ASK)],
        tool_gateway=gateway,
    )

    result = await agent("ask flow")

    assert gateway.invoke_calls == 0
    assert result.success is True
    tool_messages = [msg for msg in agent.context.stm_get() if msg.role == "tool"]
    assert tool_messages
    assert "requires hook approval" in tool_messages[0].content


@pytest.mark.asyncio
async def test_legacy_hook_adapter_keeps_runtime_compatible() -> None:
    gateway = _RecordingToolGateway()
    agent = _agent_with_single_tool_call(
        hooks=[LegacyHookAdapter(_LegacyAllowHook())],
        tool_gateway=gateway,
    )

    result = await agent("legacy flow")

    assert result.success is True
    assert gateway.invoke_calls == 1
