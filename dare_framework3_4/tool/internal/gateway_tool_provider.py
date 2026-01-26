"""Tool provider that derives tool definitions from the gateway registry."""

from __future__ import annotations

from typing import Any

from dare_framework3_4.tool.interfaces import IToolProvider
from dare_framework3_4.tool.kernel import IToolGateway
from dare_framework3_4.tool.types import CapabilityDescriptor, CapabilityType


class GatewayToolProvider(IToolProvider):
    """Expose trusted capability definitions for prompt assembly.

    Call `refresh()` to sync from the gateway before listing tools.
    """

    def __init__(self, gateway: IToolGateway) -> None:
        self._gateway = gateway
        self._capabilities: list[CapabilityDescriptor] = []

    async def refresh(self) -> list[CapabilityDescriptor]:
        """Refresh the cached capability list from the gateway."""
        self._capabilities = list(await self._gateway.list_capabilities())
        return list(self._capabilities)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions derived from cached capabilities."""
        tools: list[dict[str, Any]] = []
        for capability in self._capabilities:
            if capability.type != CapabilityType.TOOL:
                continue
            tools.append(_tool_definition(capability))
        return tools


def _tool_definition(capability: CapabilityDescriptor) -> dict[str, Any]:
    tool_def = {
        "type": "function",
        "function": {
            "name": capability.name,
            "description": capability.description,
            "parameters": capability.input_schema,
        },
        "capability_id": capability.id,
    }
    if capability.metadata:
        tool_def["metadata"] = dict(capability.metadata)
    if capability.output_schema is not None:
        tool_def["output_schema"] = dict(capability.output_schema)
    return tool_def
