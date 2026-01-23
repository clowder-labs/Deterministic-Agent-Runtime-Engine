"""hook domain stable interfaces.

Hooks are intended to be best-effort by default (v4.0 alignment note).
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework3_4.hook.types import HookPhase

HookFn = Callable[[dict[str, Any]], Any]


class IExtensionPoint(Protocol):
    def register_hook(self, phase: HookPhase, hook: HookFn) -> None: ...

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None: ...


__all__ = ["IExtensionPoint", "HookFn"]
