"""Hook plugin contracts (v2).

The Kernel defines *how* hooks are executed (`HookPhase` + callback payload). This module
defines the component-facing contract for hook plugins discovered via entrypoints.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dare_framework.core.hook import HookPhase
from dare_framework.components.plugin_system.configurable_component import IConfigurableComponent


@runtime_checkable
class IHook(IConfigurableComponent, Protocol):
    """A single hook callback bound to a Kernel phase."""

    @property
    def phase(self) -> HookPhase: ...

    def __call__(self, payload: dict[str, Any]) -> Any: ...
