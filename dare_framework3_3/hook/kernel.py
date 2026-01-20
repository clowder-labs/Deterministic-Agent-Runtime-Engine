"""Hook domain kernel interfaces."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework3_3.hook.types import HookPhase


class IExtensionPoint(Protocol):
    """[Kernel] Extension point for hook registration and emission.

    Usage: Called by the agent to register hooks and emit lifecycle signals.
    """

    def register_hook(
        self,
        phase: HookPhase,
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        """[Kernel] Register a hook callback for a phase.

        Usage: Called during agent initialization or plugin loading.
        """
        ...

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None:
        """[Kernel] Emit a hook event to registered callbacks.

        Usage: Called at lifecycle boundaries (plan/execute/etc.).
        """
        ...


__all__ = ["IExtensionPoint"]
