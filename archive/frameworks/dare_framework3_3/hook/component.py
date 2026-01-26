"""Hook domain component interfaces."""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework3_3.hook.types import HookPhase


class IHook(Protocol):
    """[Component] Hook callback bound to a kernel phase.

    Usage: Implemented by plugins to extend agent behavior.
    """

    @property
    def phase(self) -> HookPhase:
        """[Component] Phase this hook is registered for.

        Usage: Read during hook registration.
        """
        ...

    def __call__(self, payload: dict[str, Any]) -> Any:
        """[Component] Invoke the hook with the provided payload.

        Usage: Called by IExtensionPoint.emit.
        """
        ...


__all__ = ["IHook"]
