"""Hook domain component interfaces."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework3.hook.types import HookPhase


class IExtensionPoint(Protocol):
    """System-level extension point for emitting hooks."""

    def register_hook(
        self,
        phase: HookPhase,
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        ...

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None:
        ...


class IHook(Protocol):
    """A single hook callback bound to a Kernel phase."""

    @property
    def phase(self) -> HookPhase:
        ...

    def __call__(self, payload: dict[str, Any]) -> Any:
        ...


__all__ = ["IExtensionPoint", "IHook"]
