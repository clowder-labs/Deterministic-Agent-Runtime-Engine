"""Memory capability contract (v2).

Layering note:
- `IMemory` lives in `contracts/` so Kernel code (Layer 0) can depend on it without
  importing from `components/` (Layer 2).
- Implementations intended for entrypoint loading MAY also implement
  `dare_framework.components.plugin_system.configurable_component.IConfigurableComponent`
  for config-based filtering, but that is intentionally not required by this contract.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dare_framework.core.budget import Budget


@runtime_checkable
class IMemory(Protocol):
    """Retrieval and persistence surface for context engineering (Layer 2)."""

    async def retrieve(self, query: str, *, budget: Budget | None = None) -> list[dict[str, Any]]: ...

    async def add(self, items: list[dict[str, Any]]) -> None: ...

