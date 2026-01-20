"""Hook domain component interfaces (Protocol definitions)."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework3_2.hook.types import HookPhase


class IExtensionPoint(Protocol):
    """System-level extension point for emitting hooks.
    
    Manages hook registration and emission.
    """

    def register_hook(
        self,
        phase: HookPhase,
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register a hook callback for a phase.
        
        Args:
            phase: Hook phase to register for
            callback: Callback function
        """
        ...

    async def emit(self, phase: HookPhase, payload: dict[str, Any]) -> None:
        """Emit a hook event.
        
        Args:
            phase: Hook phase
            payload: Hook data
        """
        ...


class IHook(Protocol):
    """A single hook callback bound to a Kernel phase.
    
    Hooks are components that can be registered with the
    IExtensionPoint to receive callbacks at specific execution phases.
    """

    @property
    def phase(self) -> HookPhase:
        """The phase this hook is bound to."""
        ...

    def __call__(self, payload: dict[str, Any]) -> Any:
        """Execute the hook.
        
        Args:
            payload: Hook data
            
        Returns:
            Hook result (may be async)
        """
        ...
