"""MCP protocol adapter implementation."""

from __future__ import annotations

from typing import Any, Sequence

from dare_framework3_4.tool.interfaces import IMCPClient, IProtocolAdapter
from dare_framework3_4.tool.types import CapabilityDescriptor, CapabilityType, RunContext


class MCPAdapter(IProtocolAdapter):
    """MCP protocol adapter (Layer 1)."""

    def __init__(self, clients: Sequence[IMCPClient]) -> None:
        self._clients = list(clients)
        self._connected = False

    @property
    def protocol_name(self) -> str:
        return "mcp"

    async def connect(self, endpoint: str, config: dict[str, Any]) -> None:
        if self._connected:
            return
        for client in self._clients:
            await client.connect()
        self._connected = True

    async def disconnect(self) -> None:
        for client in self._clients:
            await client.disconnect()
        self._connected = False

    async def discover(self) -> Sequence[CapabilityDescriptor]:
        await self.connect(endpoint="", config={})

        capabilities: list[CapabilityDescriptor] = []
        for client in self._clients:
            for tool_def in await client.list_tools():
                name = _tool_field(tool_def, "name", "")
                description = _tool_field(tool_def, "description", "")
                input_schema = _tool_field(tool_def, "input_schema", {}) or {}
                output_schema = _tool_field(tool_def, "output_schema", None)
                risk_level = _tool_field(tool_def, "risk_level", "read_only")
                requires_approval = _tool_field(tool_def, "requires_approval", False)
                timeout_seconds = _tool_field(tool_def, "timeout_seconds", 30)
                is_work_unit = _tool_field(tool_def, "is_work_unit", False)

                capabilities.append(
                    CapabilityDescriptor(
                        id=_capability_id(client.name, name),
                        type=CapabilityType.TOOL,
                        name=name,
                        description=description,
                        input_schema=dict(input_schema),
                        output_schema=dict(output_schema) if output_schema is not None else None,
                        metadata={
                            "provider": "mcp",
                            "client": client.name,
                            "risk_level": getattr(risk_level, "value", str(risk_level)),
                            "requires_approval": bool(requires_approval),
                            "timeout_seconds": int(timeout_seconds),
                            "is_work_unit": bool(is_work_unit),
                            "capability_kind": "tool",
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
        client_name, tool_name = _parse_capability_id(capability_id)
        client = next((c for c in self._clients if c.name == client_name), None)

        if client is None:
            raise KeyError(f"Unknown MCP client: {client_name}")

        return await client.call_tool(tool_name, params, context=_noop_context())


def _capability_id(client_name: str, tool_name: str) -> str:
    return f"mcp:{client_name}:{tool_name}"


def _parse_capability_id(capability_id: str) -> tuple[str, str]:
    prefix = "mcp:"
    if not capability_id.startswith(prefix):
        raise ValueError(f"Not an MCP capability id: {capability_id}")

    rest = capability_id[len(prefix):]
    parts = rest.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid MCP capability id: {capability_id}")

    return parts[0], parts[1]


def _tool_field(tool_def: Any, field: str, default: Any) -> Any:
    if isinstance(tool_def, dict):
        return tool_def.get(field, default)
    return getattr(tool_def, field, default)


def _noop_context() -> RunContext[None]:
    return RunContext(deps=None, run_id="mcp")
