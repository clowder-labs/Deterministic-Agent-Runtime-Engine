from __future__ import annotations

from typing import Any

from dare_framework.builder.base_component import ConfigurableComponent
from dare_framework.execution.impl.hook.models import HookPhase
from dare_framework.contracts import ComponentType

from .protocols import IHook


class NoOpHook(ConfigurableComponent, IHook):
    """A hook that intentionally does nothing (useful as a placeholder)."""

    component_type = ComponentType.HOOK

    def __init__(self, phase: HookPhase) -> None:
        self._phase = phase

    @property
    def phase(self) -> HookPhase:
        return self._phase

    def __call__(self, payload: dict[str, Any]) -> Any:
        return None
