"""MCP protocol adapter implementation."""

from __future__ import annotations

from typing import Any, Sequence

from dare_framework3.tool.component import IMCPClient, IProtocolAdapter
from dare_framework3.tool.types import (
    CapabilityDescriptor,
    CapabilityType,
    RunContext,
)


class MCPAdapter(IProtocolAdapter):
    """MCP protocol adapter (Layer 1).
    
    This adapter reuses IMCPClient instances and translates
    MCP tool metadata into canonical capability descriptors.
    
    Args:
        clients: Sequence of MCP client instances
    """

    def __init__(self, clients: Sequence[IMCPClient]) -> None:
        self._clients = list(clients)
        self._connected = False

    @property
    def protocol_name(self) -> str:
        return "mcp"

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None:
        """Connect all MCP clients."""
        if self._connected:
            return
        for client in self._clients:
            await client.connect()
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect all MCP clients."""
        for client in self._clients:
            await client.disconnect()
        self._connected = False

    async def discover(self) -> Sequence[CapabilityDescriptor]:
        """Discover tools from all MCP clients."""
        await self.connect(endpoint="", config={})
        
        capabilities: list[CapabilityDescriptor] = []
        for client in self._clients:
            for tool_def in await client.list_tools():
                capabilities.append(
                    CapabilityDescriptor(
                        id=_capability_id(client.name, tool_def.name),
                        type=CapabilityType.TOOL,
                        name=tool_def.name,
                        description=tool_def.description,
                        input_schema=dict(tool_def.input_schema),
                        output_schema=dict(tool_def.output_schema),
                        metadata={
                            "provider": "mcp",
                            "client": client.name,
                            "risk_level": getattr(tool_def.risk_level, "value", str(tool_def.risk_level)),
                            "requires_approval": bool(tool_def.requires_approval),
                            "timeout_seconds": int(tool_def.timeout_seconds),
                            "is_work_unit": bool(tool_def.is_work_unit),
                        },
                    )
                )
        
        return capabilities

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> Any:
        """Invoke a tool via MCP."""
        client_name, tool_name = _parse_capability_id(capability_id)
        client = next((c for c in self._clients if c.name == client_name), None)
        
        if client is None:
            raise KeyError(f"Unknown MCP client: {client_name}")
        
        return await client.call_tool(tool_name, params, context=_noop_context())


def _capability_id(client_name: str, tool_name: str) -> str:
    """Create a capability ID for an MCP tool."""
    return f"mcp:{client_name}:{tool_name}"


def _parse_capability_id(capability_id: str) -> tuple[str, str]:
    """Parse client and tool name from capability ID."""
    prefix = "mcp:"
    if not capability_id.startswith(prefix):
        raise ValueError(f"Not an MCP capability id: {capability_id}")
    
    rest = capability_id[len(prefix):]
    parts = rest.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid MCP capability id: {capability_id}")
    
    return parts[0], parts[1]


def _noop_context() -> RunContext[None]:
    """Create a minimal run context for MCP calls."""
    return RunContext(deps=None, run_id="mcp")
