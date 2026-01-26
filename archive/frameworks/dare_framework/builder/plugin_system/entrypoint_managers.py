"""Entrypoint-backed plugin manager implementations (v2).

The framework uses Python entrypoints as the extension mechanism. This module
implements minimal, deterministic loaders for the v2 entrypoint groups, while
keeping the Kernel (Layer 0) free of any `importlib.metadata` dependency.

MVP notes:
- Managers focus on discovery + selection semantics (config-driven).
- Component async initialization is intentionally out-of-scope for now; managers
  return constructed instances and let higher layers decide when to `await init()`.
"""

from __future__ import annotations

from importlib import metadata
from typing import Any, Callable, Iterable

from dare_framework.config import Config
from dare_framework.model.components import IModelAdapter
from dare_framework.tool.components import ITool
from dare_framework.builder.plugin_system.configurable_component import IConfigurableComponent
from dare_framework.builder.plugin_system.entrypoints import (
    ENTRYPOINT_V2_MODEL_ADAPTERS,
    ENTRYPOINT_V2_TOOLS,
    ENTRYPOINT_V2_VALIDATORS,
)
from dare_framework.builder.plugin_system.managers import IModelAdapterManager, IToolManager, IValidatorManager

EntryPointLoader = Callable[[], Any]


class EntrypointToolManager(IToolManager):
    """Load `ITool` implementations from the v2 tools entrypoint group."""

    def __init__(self, *, entry_points_loader: EntryPointLoader | None = None) -> None:
        self._entry_points_loader = entry_points_loader or metadata.entry_points

    def load_tools(self, *, config: Any | None = None) -> list[object]:
        components = _load_group(self._entry_points_loader, ENTRYPOINT_V2_TOOLS)
        enabled = [comp for comp in components if _is_enabled(comp, config)]
        tools = [comp for comp in enabled if isinstance(comp, ITool)]
        return sorted(tools, key=lambda tool: getattr(tool, "order", 100))


class EntrypointModelAdapterManager(IModelAdapterManager):
    """Load a single `IModelAdapter` selected by config.

    Selection rule (v2):
    - `Config.llm.adapter` selects the entrypoint name.
    """

    def __init__(self, *, entry_points_loader: EntryPointLoader | None = None) -> None:
        self._entry_points_loader = entry_points_loader or metadata.entry_points

    def load_model_adapter(self, *, config: Any | None = None) -> object | None:
        adapter_name = _configured_model_adapter(config)
        if not adapter_name:
            return None

        entry_point = _find_entry_point(self._entry_points_loader, ENTRYPOINT_V2_MODEL_ADAPTERS, adapter_name)
        instance = _instantiate_entry_point(entry_point)
        if not isinstance(instance, IModelAdapter):
            raise TypeError(
                f"Entrypoint '{ENTRYPOINT_V2_MODEL_ADAPTERS}:{adapter_name}' did not load an IModelAdapter"
            )
        if not _is_enabled(instance, config):
            raise RuntimeError(f"Configured model adapter '{adapter_name}' is disabled by config")
        return instance


class EntrypointValidatorManager(IValidatorManager):
    """Load all enabled validators as an ordered collection."""

    def __init__(self, *, entry_points_loader: EntryPointLoader | None = None) -> None:
        self._entry_points_loader = entry_points_loader or metadata.entry_points

    def load_validators(self, *, config: Any | None = None) -> list[object]:
        components = _load_group(self._entry_points_loader, ENTRYPOINT_V2_VALIDATORS)
        enabled = [comp for comp in components if _is_enabled(comp, config)]
        return sorted(enabled, key=lambda comp: getattr(comp, "order", 100))


def _configured_model_adapter(config: Any | None) -> str | None:
    if isinstance(config, Config):
        return config.llm.adapter
    if isinstance(config, dict):
        llm = config.get("llm")
        if isinstance(llm, dict):
            adapter = llm.get("adapter")
            if isinstance(adapter, str) and adapter.strip():
                return adapter.strip()
    return None


def _is_enabled(component: object, config: Any | None) -> bool:
    if config is None:
        return True
    if not isinstance(component, IConfigurableComponent):
        return True
    if isinstance(config, Config):
        return config.is_component_enabled(component.component_type, component.component_name)
    return True


def _load_group(loader: EntryPointLoader, group: str) -> list[object]:
    return [_instantiate_entry_point(ep) for ep in _iter_entry_points(loader, group)]


def _find_entry_point(loader: EntryPointLoader, group: str, name: str):
    for ep in _iter_entry_points(loader, group):
        if getattr(ep, "name", None) == name:
            return ep
    raise KeyError(f"Entrypoint not found: {group}:{name}")


def _iter_entry_points(loader: EntryPointLoader, group: str) -> Iterable[Any]:
    entry_points = loader()
    if hasattr(entry_points, "select"):
        return list(entry_points.select(group=group))
    return list(entry_points.get(group, []))


def _instantiate_entry_point(entry_point: Any) -> object:
    loaded = entry_point.load()
    if isinstance(loaded, type):
        return loaded()
    if callable(loaded):
        return loaded()
    raise TypeError(f"Unsupported entrypoint payload for {getattr(entry_point, 'name', '<unknown>')}")
