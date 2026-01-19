"""Configurable component identity contract (v2).

This is used by config filtering/selection in plugin managers.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework.components.plugin_system.component import IComponent
from dare_framework.contracts import ComponentType


@runtime_checkable
class IConfigurableComponent(IComponent, Protocol):
    """Entrypoint component with stable config identity."""

    @property
    def component_type(self) -> ComponentType: ...

    @property
    def component_name(self) -> str: ...
