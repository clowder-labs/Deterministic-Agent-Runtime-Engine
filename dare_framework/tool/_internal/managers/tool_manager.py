"""Tool manager for trusted capability registry and provider aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from dare_framework.tool.interfaces import ICapabilityProvider, ITool, IToolManager, IToolProvider
from dare_framework.tool.types import (
    CapabilityDescriptor,
    CapabilityKind,
    CapabilityMetadata,
    CapabilityType,
    ProviderStatus,
    ToolDefinition,
)

_TOOL_SOURCE = object()


@dataclass
class _registry_entry:
    descriptor: CapabilityDescriptor
    enabled: bool
    source: object


class ToolManager(IToolManager, IToolProvider):
    """Owns the trusted capability registry and exposes tool definitions."""

    def __init__(self, *, namespace: str | None = "tool") -> None:
        self._namespace = namespace or ""
        self._registry: dict[str, _registry_entry] = {}
        self._providers: list[ICapabilityProvider] = []
        self._provider_capabilities: dict[ICapabilityProvider, set[str]] = {}

    def register_tool(
        self,
        tool: ITool,
        *,
        namespace: str | None = None,
        version: str | None = None,
    ) -> CapabilityDescriptor:
        capability_id = _capability_id(
            namespace if namespace is not None else self._namespace,
            tool.name,
            version,
        )
        if capability_id in self._registry:
            raise ValueError(f"Capability already registered: {capability_id}")
        descriptor = _descriptor_from_tool(tool, capability_id)
        self._registry[capability_id] = _registry_entry(
            descriptor=descriptor,
            enabled=True,
            source=_TOOL_SOURCE,
        )
        return descriptor

    def unregister_tool(self, capability_id: str) -> bool:
        entry = self._registry.get(capability_id)
        if entry is None:
            return False
        if entry.source is not _TOOL_SOURCE:
            raise ValueError("Cannot unregister provider-owned capability")
        del self._registry[capability_id]
        return True

    def update_tool(
        self,
        tool: ITool,
        *,
        capability_id: str,
        enabled: bool | None = None,
    ) -> CapabilityDescriptor:
        entry = self._registry.get(capability_id)
        if entry is None:
            raise KeyError(f"Unknown capability id: {capability_id}")
        if entry.source is not _TOOL_SOURCE:
            raise ValueError("Cannot update provider-owned capability")
        descriptor = _descriptor_from_tool(tool, capability_id)
        entry.descriptor = descriptor
        if enabled is not None:
            entry.enabled = enabled
        return descriptor

    def set_capability_enabled(self, capability_id: str, enabled: bool) -> None:
        entry = self._registry.get(capability_id)
        if entry is None:
            raise KeyError(f"Unknown capability id: {capability_id}")
        entry.enabled = enabled

    def register_provider(self, provider: ICapabilityProvider) -> None:
        if not isinstance(provider, ICapabilityProvider):
            raise TypeError(f"Provider must implement ICapabilityProvider, got {type(provider)}")
        if provider in self._providers:
            return
        self._providers.append(provider)
        self._provider_capabilities.setdefault(provider, set())

    def unregister_provider(self, provider: ICapabilityProvider) -> bool:
        if provider not in self._providers:
            return False
        self._providers.remove(provider)
        for capability_id in self._provider_capabilities.get(provider, set()):
            entry = self._registry.get(capability_id)
            if entry and entry.source is provider:
                del self._registry[capability_id]
        self._provider_capabilities.pop(provider, None)
        return True

    async def refresh(self) -> list[CapabilityDescriptor]:
        for provider in self._providers:
            capabilities = list(await provider.list())
            self._sync_provider_capabilities(provider, capabilities)
        return self.list_capabilities(include_disabled=True)

    def list_capabilities(self, *, include_disabled: bool = False) -> list[CapabilityDescriptor]:
        descriptors: list[CapabilityDescriptor] = []
        for entry in self._registry.values():
            if not include_disabled and not entry.enabled:
                continue
            descriptors.append(entry.descriptor)
        return descriptors

    def list_tool_defs(self) -> list[ToolDefinition]:
        tool_defs: list[ToolDefinition] = []
        for entry in self._registry.values():
            if not entry.enabled:
                continue
            capability = entry.descriptor
            if capability.type != CapabilityType.TOOL:
                continue
            tool_defs.append(_tool_definition(capability))
        return tool_defs

    def list_tools(self) -> list[dict[str, Any]]:
        """Alias for BaseContext compatibility."""
        return list(self.list_tool_defs())

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
        for index, provider in enumerate(self._providers):
            name = getattr(provider, "name", f"provider_{index}")
            try:
                results[str(name)] = await provider.health_check()
            except Exception:
                results[str(name)] = ProviderStatus.UNKNOWN
        return results

    def _sync_provider_capabilities(
        self,
        provider: ICapabilityProvider,
        capabilities: list[CapabilityDescriptor],
    ) -> None:
        existing_ids = self._provider_capabilities.get(provider, set())
        incoming_ids: set[str] = set()
        for capability in capabilities:
            if capability.id in incoming_ids:
                raise ValueError(f"Duplicate capability id: {capability.id}")
            incoming_ids.add(capability.id)
            entry = self._registry.get(capability.id)
            if entry is not None and entry.source is not provider:
                raise ValueError(f"Duplicate capability id: {capability.id}")
            # Preserve enable/disable state across refreshes while updating metadata.
            enabled = entry.enabled if entry is not None else True
            self._registry[capability.id] = _registry_entry(
                descriptor=capability,
                enabled=enabled,
                source=provider,
            )
        # Remove capabilities that disappeared from the provider during refresh.
        for capability_id in existing_ids - incoming_ids:
            entry = self._registry.get(capability_id)
            if entry and entry.source is provider:
                del self._registry[capability_id]
        self._provider_capabilities[provider] = incoming_ids


def _capability_id(namespace: str, name: str, version: str | None) -> str:
    if namespace:
        base = f"{namespace}:{name}"
    else:
        base = name
    if version:
        return f"{base}@{version}"
    return base


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
    return metadata


def _tool_definition(capability: CapabilityDescriptor) -> ToolDefinition:
    tool_def: ToolDefinition = {
        "type": "function",
        "function": {
            "name": capability.name,
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


__all__ = ["ToolManager"]
