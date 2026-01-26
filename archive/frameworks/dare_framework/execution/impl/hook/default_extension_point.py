from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from dare_framework.execution.impl.hook.models import HookPhase
from dare_framework.execution.impl.hook.protocols import IExtensionPoint


class DefaultExtensionPoint(IExtensionPoint):
    """In-process hook registry for Kernel phases (MVP)."""

    def __init__(self) -> None:
        self._hooks: dict[HookPhase, list[Callable[[dict[str, Any]], Any]]] = defaultdict(list)

    def register_hook(self, phase: HookPhase, callback: Callable[[dict[str, Any]], Any]) -> None:
        self._hooks[phase].append(callback)

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None:
        # Hooks are best-effort: failures should not crash the Kernel by default.
        for callback in self._hooks.get(phase, []):
            try:
                result = callback(payload)
                if hasattr(result, "__await__"):
                    await result
            except Exception:  # noqa: BLE001
                continue
