"""Tool provider derived from gateway capability descriptors."""

from __future__ import annotations

from typing import Any, Iterable

from dare_framework.tool.interfaces import IToolProvider
from dare_framework.tool.types import CapabilityDescriptor


class GatewayToolProvider(IToolProvider):
    """Expose tool definitions derived from gateway capabilities."""

    def __init__(self, *, capabilities: Iterable[CapabilityDescriptor]) -> None:
        self._capabilities = list(capabilities)

    def list_tools(self) -> list[dict[str, Any]]:
        return [_tool_definition(capability) for capability in self._capabilities]


def _tool_definition(capability: CapabilityDescriptor) -> dict[str, Any]:
    tool_def: dict[str, Any] = {
        "name": capability.name,
        "description": capability.description,
        "parameters": capability.input_schema,
        "capability_id": capability.id,
    }
    if capability.output_schema is not None:
        tool_def["output_schema"] = capability.output_schema
    if capability.metadata:
        tool_def["metadata"] = dict(capability.metadata)
    return tool_def


__all__ = ["GatewayToolProvider"]
