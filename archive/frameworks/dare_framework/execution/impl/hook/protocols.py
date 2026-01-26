"""Kernel hook protocols (v2)."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework.execution.impl.hook.models import HookPhase


class IExtensionPoint(Protocol):
    """System-level extension point for emitting hooks (v2.0)."""

    def register_hook(self, phase: HookPhase, callback: Callable[[dict[str, Any]], Any]) -> None: ...

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None: ...
