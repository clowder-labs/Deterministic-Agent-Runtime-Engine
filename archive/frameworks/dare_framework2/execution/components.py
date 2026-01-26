"""Execution domain component interfaces."""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework2.execution.types import HookPhase


class IHook(Protocol):
    """A single hook callback bound to a Kernel phase."""

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
