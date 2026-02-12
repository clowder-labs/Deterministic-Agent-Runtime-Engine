from __future__ import annotations

from typing import Any

import pytest

from dare_framework.hook._internal.hook_extension_point import HookExtensionPoint
from dare_framework.hook._internal.legacy_adapter import LegacyHookAdapter
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.infra.component import ComponentType


class _LegacyHook:
    @property
    def name(self) -> str:
        return "legacy-hook"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> dict[str, Any]:
        _ = (phase, args, kwargs)
        return {"legacy": True}


class _BlockingHook:
    @property
    def name(self) -> str:
        return "blocking-hook"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookResult:
        _ = (phase, args, kwargs)
        return HookResult(decision=HookDecision.BLOCK)


@pytest.mark.asyncio
async def test_legacy_hook_defaults_to_allow_in_v1_dispatch() -> None:
    adapter = LegacyHookAdapter(_LegacyHook())
    result = await adapter.invoke(HookPhase.BEFORE_TOOL, payload={"tool_name": "bash"})
    assert result.decision is HookDecision.ALLOW


@pytest.mark.asyncio
async def test_shadow_mode_does_not_enforce_block_decision() -> None:
    extension_point = HookExtensionPoint([_BlockingHook()], enforce=False)
    result = await extension_point.emit(
        HookPhase.BEFORE_TOOL,
        {"tool_name": "bash", "tool_call_id": "c1", "capability_id": "shell"},
    )
    assert result.decision is HookDecision.ALLOW
    assert result.message is not None and "shadow" in result.message
