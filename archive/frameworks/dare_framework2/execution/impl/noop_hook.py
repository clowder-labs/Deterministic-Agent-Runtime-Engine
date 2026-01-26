"""No-op hook implementation."""

from __future__ import annotations

from typing import Any

from dare_framework2.execution.components import IHook
from dare_framework2.execution.types import HookPhase


class NoOpHook(IHook):
    """A hook that intentionally does nothing.
    
    Useful as a placeholder or for testing.
    
    Args:
        phase: The hook phase this instance is bound to
    """

    def __init__(self, phase: HookPhase) -> None:
        self._phase = phase

    @property
    def phase(self) -> HookPhase:
        """The phase this hook is bound to."""
        return self._phase

    def __call__(self, payload: dict[str, Any]) -> Any:
        """Does nothing."""
        return None
