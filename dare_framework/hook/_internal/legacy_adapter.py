"""Adapter to run legacy hooks in V1 governance dispatch."""

from __future__ import annotations

from typing import Any, Literal

from dare_framework.hook.kernel import IHook
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.infra.component import ComponentType


class LegacyHookAdapter(IHook):
    """Wrap legacy hooks and normalize them to HookResult allow responses."""

    def __init__(self, legacy_hook: IHook) -> None:
        self._legacy_hook = legacy_hook

    @property
    def name(self) -> str:
        return getattr(self._legacy_hook, "name", "legacy_hook")

    @property
    def component_type(self) -> Literal[ComponentType.HOOK]:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookResult:
        await self._legacy_hook.invoke(phase, *args, **kwargs)
        return HookResult(decision=HookDecision.ALLOW)


__all__ = ["LegacyHookAdapter"]
