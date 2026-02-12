import asyncio

import pytest

from dare_framework.hook._internal.hook_extension_point import HookExtensionPoint
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.infra.component import ComponentType


class _StubHook:
    def __init__(self, name: str, behavior):
        self._name = name
        self._behavior = behavior

    @property
    def name(self) -> str:
        return self._name

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args, **kwargs):  # noqa: ANN002, ANN003
        payload = kwargs.get("payload", {})
        return await self._behavior(phase, payload)


@pytest.mark.asyncio
async def test_emit_returns_aggregated_decision() -> None:
    async def blocker(_phase: HookPhase, _payload: dict[str, object]) -> HookResult:
        return HookResult(decision=HookDecision.BLOCK)

    ep = HookExtensionPoint([_StubHook("blocker", blocker)])
    result = await ep.emit(
        HookPhase.BEFORE_TOOL,
        {"tool_name": "bash", "tool_call_id": "c1", "capability_id": "shell"},
    )
    assert result.decision.value == "block"


@pytest.mark.asyncio
async def test_emit_downgrades_timeout_to_allow() -> None:
    async def slow(_phase: HookPhase, _payload: dict[str, object]) -> HookResult:
        await asyncio.sleep(0.1)
        return HookResult(decision=HookDecision.BLOCK)

    ep = HookExtensionPoint([_StubHook("slow", slow)], timeout_ms=1)
    result = await ep.emit(HookPhase.BEFORE_TOOL, {"tool_name": "bash", "tool_call_id": "c1", "capability_id": "shell"})
    assert result.decision is HookDecision.ALLOW
    assert result.message is not None and "HOOK_TIMEOUT" in result.message


@pytest.mark.asyncio
async def test_emit_downgrades_runtime_error_to_allow() -> None:
    async def broken(_phase: HookPhase, _payload: dict[str, object]) -> HookResult:
        raise RuntimeError("boom")

    ep = HookExtensionPoint([_StubHook("broken", broken)])
    result = await ep.emit(HookPhase.BEFORE_TOOL, {"tool_name": "bash", "tool_call_id": "c1", "capability_id": "shell"})
    assert result.decision is HookDecision.ALLOW
    assert result.message is not None and "HOOK_RUNTIME_ERROR" in result.message
