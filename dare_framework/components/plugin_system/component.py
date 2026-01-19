"""Base lifecycle contract for plugin-extensible components (v2).

This lives outside the Kernel so that Kernel code does not depend on plugin discovery
or component initialization mechanics.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")


@runtime_checkable
class IComponent(Protocol):
    """Minimal lifecycle contract for components loaded via entrypoints."""

    @property
    def order(self) -> int: ...

    async def init(self, config: object | None = None, prompts: object | None = None) -> None: ...

    def register(self, registrar: "IComponentRegistrar") -> None: ...

    async def close(self) -> None: ...


@runtime_checkable
class IComponentRegistrar(Protocol):
    """Registrar used by component managers during loading/assembly."""

    def register_component(self, component: IComponent) -> None: ...
