"""Default extension point implementation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from dare_framework2.execution.interfaces import IExtensionPoint
from dare_framework2.execution.types import HookPhase


class DefaultExtensionPoint(IExtensionPoint):
    """In-process hook registry for Kernel phases.
    
    Hooks are best-effort: failures do not crash the Kernel.
    """

    def __init__(self) -> None:
        self._hooks: dict[HookPhase, list[Callable[[dict[str, Any]], Any]]] = defaultdict(list)

    def register_hook(
        self,
        phase: HookPhase,
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register a hook callback for a phase."""
        self._hooks[phase].append(callback)

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None:
        """Emit a hook event to all registered callbacks.
        
        Callbacks are best-effort: failures are silently ignored.
        """
        for callback in self._hooks.get(phase, []):
            try:
                result = callback(payload)
                if hasattr(result, "__await__"):
                    await result
            except Exception:  # noqa: BLE001
                # Best-effort: don't crash on hook failures
                continue
