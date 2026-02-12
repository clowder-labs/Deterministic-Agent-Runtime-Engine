"""Tool manager for trusted capability registry and runtime invocation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from importlib import metadata as importlib_metadata
from typing import Any, Callable, Iterable

from dare_framework.config.types import Config
from dare_framework.tool.kernel import ITool, IToolManager, IToolProvider
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    CapabilityMetadata,
    CapabilityType,
    ProviderStatus,
    ToolDefinition,
)

logger = logging.getLogger(__name__)

ENTRYPOINT_TOOL_PROVIDERS = "dare_framework.tool_providers"

_TOOL_SOURCE = object()


@dataclass
class _registry_entry:
    descriptor: CapabilityDescriptor
    enabled: bool
    source: object
    tool: ITool | None = None


class ToolManager(IToolManager):
    """Owns the trusted capability registry and tool/provider lifecycle."""

    def __init__(
            self,
            *,
            config: Config | None = None,
            namespace: str | None = None,
            entrypoint_group: str = ENTRYPOINT_TOOL_PROVIDERS,
            entry_points_loader: Callable[[], Any] | None = None,
            load_entrypoints: bool = True,
    ) -> None:
        self._config = config
        self._namespace = namespace or ""
        self._registry: dict[str, _registry_entry] = {}
        self._tool_index_by_object: dict[int, str] = {}
        self._providers: list[IToolProvider] = []
        self._provider_capabilities: dict[IToolProvider, set[str]] = {}
        self._entrypoint_group = entrypoint_group
        self._entry_points_loader = entry_points_loader or _default_entry_points_loader
        self._load_entrypoints = load_entrypoints
        self._entrypoints_loaded = False
        self._entrypoint_providers: dict[str, IToolProvider] = {}
        if load_entrypoints:
            self.load_entrypoint_providers()

    def load_entrypoint_providers(self) -> None:
        """Load tool providers registered via Python entry points."""
        if not self._load_entrypoints or self._entrypoints_loaded:
            return
        self._entrypoints_loaded = True

        entry_points = _select_entry_points(self._entry_points_loader(), self._entrypoint_group)
        for entry_point in entry_points:
            name = getattr(entry_point, "name", None)
            key = str(name) if isinstance(name, str) else str(getattr(entry_point, "value", id(entry_point)))
            if key in self._entrypoint_providers:
                continue
            provider = _load_entrypoint_provider(entry_point)
            if provider is None:
                continue
            self._entrypoint_providers[key] = provider
            self.register_provider(provider)

    def register_tool(
            self,
            tool: ITool,
            *,
            namespace: str | None = None,
            version: str | None = None,
    ) -> CapabilityDescriptor:
        existing_id = self._tool_index_by_object.get(id(tool))
        if existing_id:
            entry = self._registry.get(existing_id)
            if entry is not None:
                return entry.descriptor
        capability_id = tool.name
        if capability_id in self._registry:
            raise ValueError(f"Tool name already registered: {tool.name}")
        descriptor = _descriptor_from_tool(tool, capability_id)
        self._registry[capability_id] = _registry_entry(
            descriptor=descriptor,
            enabled=True,
            source=_TOOL_SOURCE,
            tool=tool,
        )
        self._tool_index_by_object[id(tool)] = capability_id
        return descriptor

    def unregister_tool(self, capability_id: str) -> bool:
        entry = self._registry.get(capability_id)
        if entry is None:
            return False
        if entry.source is not _TOOL_SOURCE:
            raise ValueError("Cannot unregister provider-owned capability")
        self._remove_entry(capability_id)
        return True

    def update_tool(
            self,
            tool: ITool,
            *,
            capability_id: str,
            enabled: bool | None = None,
    ) -> CapabilityDescriptor:
        if tool.name != capability_id:
            raise ValueError(
                f"Tool name must match capability id: {tool.name} != {capability_id}"
            )
        entry = self._registry.get(capability_id)
        if entry is None:
            raise KeyError(f"Unknown capability id: {capability_id}")
        if entry.source is not _TOOL_SOURCE:
            raise ValueError("Cannot update provider-owned capability")
        old_tool = entry.tool
        descriptor = _descriptor_from_tool(tool, capability_id)
        entry.descriptor = descriptor
        entry.tool = tool
        if enabled is not None:
            entry.enabled = enabled
        if old_tool is not None and id(old_tool) != id(tool):
            self._tool_index_by_object.pop(id(old_tool), None)
        self._tool_index_by_object[id(tool)] = capability_id
        return descriptor

    def change_capability_status(self, capability_id: str, enabled: bool) -> None:
        entry = self._registry.get(capability_id)
        if entry is None:
            raise KeyError(f"Unknown capability id: {capability_id}")
        entry.enabled = enabled

    def register_provider(self, provider: IToolProvider) -> None:
        if provider in self._providers:
            return
        self._providers.append(provider)
        self._provider_capabilities.setdefault(provider, set())
        self._sync_provider_tools(provider, provider.list_tools())

    def unregister_provider(self, provider: IToolProvider) -> bool:
        if provider not in self._providers:
            return False
        self._providers.remove(provider)
        for capability_id in self._provider_capabilities.get(provider, set()):
            entry = self._registry.get(capability_id)
            if entry and entry.source is provider:
                self._remove_entry(capability_id)
        self._provider_capabilities.pop(provider, None)
        return True

    async def refresh(self) -> list[CapabilityDescriptor]:
        self.load_entrypoint_providers()
        for provider in self._providers:
            self._sync_provider_tools(provider, provider.list_tools())
        return self.list_capabilities(include_disabled=True)

    def load_tools(self, *, config: Config | None = None) -> list[ITool]:
        self.load_entrypoint_providers()
        tools: list[ITool] = []
        for entry in self._registry.values():
            if not entry.enabled or entry.tool is None:
                continue
            tools.append(entry.tool)
        return tools

    def get_tool(self, capability_id: str) -> ITool:
        entry = self._registry.get(capability_id)
        if entry is None or not entry.enabled or entry.tool is None:
            raise KeyError(f"Unknown capability id: {capability_id}")
        return entry.tool

    def list_capabilities(self, *, include_disabled: bool = False) -> list[CapabilityDescriptor]:
        descriptors: list[CapabilityDescriptor] = []
        for entry in self._registry.values():
            if not include_disabled and not entry.enabled:
                continue
            descriptors.append(entry.descriptor)
        return descriptors

    def list_tools(self) -> list[ITool]:
        """Return active tools for inspection or provider-style access."""
        tools: list[ITool] = []
        for entry in self._registry.values():
            if not entry.enabled or entry.tool is None:
                continue
            tools.append(entry.tool)
        return tools

    def get_capability(
            self,
            capability_id: str,
            *,
            include_disabled: bool = False,
    ) -> CapabilityDescriptor | None:
        entry = self._registry.get(capability_id)
        if entry is None:
            return None
        if not include_disabled and not entry.enabled:
            return None
        return entry.descriptor

    async def health_check(self) -> dict[str, ProviderStatus]:
        results: dict[str, ProviderStatus] = {}
        if self._providers:
            for index, provider in enumerate(self._providers):
                name = getattr(provider, "name", f"provider_{index}")
                results[str(name)] = ProviderStatus.UNKNOWN
        results.setdefault(
            "tool_manager",
            ProviderStatus.HEALTHY if self._registry else ProviderStatus.DEGRADED,
        )
        return results

    def _sync_provider_tools(self, provider: IToolProvider, tools: list[ITool]) -> None:
        existing_ids = self._provider_capabilities.get(provider, set())
        incoming_ids: set[str] = set()
        for tool in tools:
            capability_id = self._register_provider_tool(provider, tool)
            entry = self._registry.get(capability_id)
            if entry and entry.source is provider:
                incoming_ids.add(capability_id)
        for capability_id in existing_ids - incoming_ids:
            entry = self._registry.get(capability_id)
            if entry and entry.source is provider:
                self._remove_entry(capability_id)
        self._provider_capabilities[provider] = incoming_ids

    def _register_provider_tool(self, provider: IToolProvider, tool: ITool) -> str:
        existing_id = self._tool_index_by_object.get(id(tool))
        if existing_id:
            return existing_id
        capability_id = tool.name
        if capability_id in self._registry:
            raise ValueError(f"Tool name already registered: {tool.name}")
        descriptor = _descriptor_from_tool(tool, capability_id)
        self._registry[capability_id] = _registry_entry(
            descriptor=descriptor,
            enabled=True,
            source=provider,
            tool=tool,
        )
        self._tool_index_by_object[id(tool)] = capability_id
        return capability_id

    def _remove_entry(self, capability_id: str) -> None:
        entry = self._registry.pop(capability_id, None)
        if entry and entry.tool is not None:
            self._tool_index_by_object.pop(id(entry.tool), None)


def _default_entry_points_loader() -> Any:
    try:
        return importlib_metadata.entry_points()
    except Exception:
        return ()


def _select_entry_points(entry_points: Any, group: str) -> Iterable[Any]:
    if entry_points is None:
        return []
    selector = getattr(entry_points, "select", None)
    if callable(selector):
        return selector(group=group)
    if isinstance(entry_points, dict):
        return entry_points.get(group, [])
    try:
        return [ep for ep in entry_points if getattr(ep, "group", None) == group]
    except TypeError:
        return []


def _load_entrypoint_provider(entry_point: Any) -> IToolProvider | None:
    try:
        loaded = entry_point.load()
    except Exception as exc:
        logger.warning("Failed to load tool provider entry point %r: %s", entry_point, exc)
        return None

    if isinstance(loaded, IToolProvider):
        return loaded

    if callable(loaded):
        try:
            provider = loaded()
        except Exception as exc:
            logger.warning("Failed to instantiate tool provider from %r: %s", entry_point, exc)
            return None
        if isinstance(provider, IToolProvider):
            return provider

    logger.warning("Entry point %r did not return an IToolProvider", entry_point)
    return None


def _descriptor_from_tool(tool: ITool, capability_id: str) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        id=capability_id,
        type=CapabilityType.TOOL,
        name=tool.name,
        description=tool.description,
        input_schema=tool.input_schema,
        output_schema=tool.output_schema,
        metadata=_capability_metadata(tool),
    )


def _capability_metadata(tool: ITool) -> CapabilityMetadata:
    metadata: CapabilityMetadata = {}
    risk_level = getattr(tool, "risk_level", "read_only")
    metadata["risk_level"] = str(getattr(risk_level, "value", risk_level))
    metadata["requires_approval"] = bool(getattr(tool, "requires_approval", False))
    timeout_seconds = getattr(tool, "timeout_seconds", None)
    if timeout_seconds is not None:
        metadata["timeout_seconds"] = int(timeout_seconds)
    metadata["is_work_unit"] = bool(getattr(tool, "is_work_unit", False))
    metadata["capability_kind"] = _normalize_capability_kind(
        getattr(tool, "capability_kind", CapabilityKind.TOOL)
    )
    metadata["display_name"] = getattr(tool, "name", "")
    return metadata


def _tool_definition(capability: CapabilityDescriptor) -> ToolDefinition:
    tool_def: ToolDefinition = {
        "type": "function",
        "function": {
            "name": capability.id,
            "description": capability.description,
            "parameters": capability.input_schema,
        },
        "capability_id": capability.id,
    }
    if capability.metadata:
        tool_def["metadata"] = _normalize_metadata(dict(capability.metadata))
    if capability.output_schema is not None:
        tool_def["output_schema"] = dict(capability.output_schema)
    return tool_def


def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized[key] = _normalize_value(value)
    return normalized


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def _normalize_capability_kind(value: Any) -> CapabilityKind:
    if isinstance(value, CapabilityKind):
        return value
    if hasattr(value, "value"):
        value = value.value
    try:
        return CapabilityKind(str(value))
    except ValueError:
        return CapabilityKind.TOOL


__all__ = ["ENTRYPOINT_TOOL_PROVIDERS", "ToolManager"]
