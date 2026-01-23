"""config domain pluggable interfaces (Layer 3 managers).

v4.0 alignment note:
- Managers are responsible for deterministic assembly:
  discovery (entrypoints), selection, filtering, ordering, instantiation.
- Kernel (Layer 0) should not depend on entrypoints discovery.

This module declares manager interface *shapes* only; concrete plugin systems are
out of scope unless explicitly requested.
"""

from __future__ import annotations

from typing import Any, Protocol


class IToolManager(Protocol):
    """Loads tool capability implementations."""

    def load_tools(self, *, config: Any | None = None) -> list[object]: ...


class IModelAdapterManager(Protocol):
    """Loads the model adapter implementation (single-select)."""

    def load_model_adapter(self, *, config: Any | None = None) -> object | None: ...


class IPlannerManager(Protocol):
    """Loads a planner strategy implementation (single-select)."""

    def load_planner(self, *, config: Any | None = None) -> object | None: ...


class IValidatorManager(Protocol):
    """Loads validator strategy implementations (multi-load)."""

    def load_validators(self, *, config: Any | None = None) -> list[object]: ...


class IRemediatorManager(Protocol):
    """Loads a remediation strategy implementation (single-select)."""

    def load_remediator(self, *, config: Any | None = None) -> object | None: ...


class IProtocolAdapterManager(Protocol):
    """Loads protocol adapters (multi-load)."""

    def load_protocol_adapters(self, *, config: Any | None = None) -> list[object]: ...


class IHookManager(Protocol):
    """Loads hook plugins (multi-load)."""

    def load_hooks(self, *, config: Any | None = None) -> list[object]: ...


__all__ = [
    "IHookManager",
    "IModelAdapterManager",
    "IPlannerManager",
    "IProtocolAdapterManager",
    "IRemediatorManager",
    "IToolManager",
    "IValidatorManager",
]
