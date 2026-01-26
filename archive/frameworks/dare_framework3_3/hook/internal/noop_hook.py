"""No-op hook implementation."""

from __future__ import annotations

from typing import Any

from dare_framework3_3.hook.component import IHook
from dare_framework3_3.hook.types import HookPhase


class NoOpHook(IHook):
    """A hook that intentionally does nothing."""

    def __init__(self, phase: HookPhase) -> None:
        self._phase = phase

    @property
    def phase(self) -> HookPhase:
        return self._phase

    def __call__(self, payload: dict[str, Any]) -> Any:
        _ = payload
        return None
