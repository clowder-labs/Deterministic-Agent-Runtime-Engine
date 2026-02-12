"""MCP tool manager integration."""

from __future__ import annotations

from typing import Sequence

from dare_framework.mcp.kernel import IMCPClient
from dare_framework.tool.kernel import ITool, IToolProvider


class McpToolManager(IToolProvider):
    """Manage MCP clients and expose their tools as a provider."""

    def __init__(self, clients: Sequence[IMCPClient]) -> None:
        self._clients: dict[str, IMCPClient] = {client.name: client for client in clients}
        self._tools_by_mcp: dict[str, dict[str, ITool]] = {name: {} for name in self._clients}
        self._disabled_mcps: set[str] = set()
        self._connected_mcps: set[str] = set()

    async def initialize(self) -> None:
        """Connect enabled MCP clients and cache tools."""
        for mcp_name in self._clients:
            if mcp_name in self._disabled_mcps:
                self._tools_by_mcp[mcp_name] = {}
                continue
            await self._refresh_mcp(mcp_name)

    async def close(self) -> None:
        """Disconnect all MCP clients."""
        for mcp_name, client in self._clients.items():
            if mcp_name in self._connected_mcps:
                await client.disconnect()
        self._connected_mcps.clear()

    async def reload(self, mcp_name: str | None = None) -> None:
        """Reload all enabled MCPs, or a single MCP by name."""
        if mcp_name is None:
            for name in self._clients:
                if name in self._disabled_mcps:
                    continue
                await self._refresh_mcp(name)
            return
        self._ensure_known_mcp(mcp_name)
        if mcp_name in self._disabled_mcps:
            self._tools_by_mcp[mcp_name] = {}
            return
        await self._refresh_mcp(mcp_name)

    async def set_mcp_enabled(self, mcp_name: str, *, enabled: bool) -> None:
        """Enable or disable a specific MCP at runtime."""
        self._ensure_known_mcp(mcp_name)
        if enabled:
            self._disabled_mcps.discard(mcp_name)
            await self._refresh_mcp(mcp_name)
            return
        self._disabled_mcps.add(mcp_name)
        self._tools_by_mcp[mcp_name] = {}
        if mcp_name in self._connected_mcps:
            await self._clients[mcp_name].disconnect()
            self._connected_mcps.discard(mcp_name)

    def list_mcp_names(self, *, include_disabled: bool = False) -> list[str]:
        names = sorted(self._clients)
        if include_disabled:
            return names
        return [name for name in names if name not in self._disabled_mcps]

    def list_tools(self, mcp_name: str | None = None) -> list[ITool]:
        """Return cached tools, optionally scoped to one MCP."""
        if mcp_name is None:
            tools: list[ITool] = []
            seen: set[int] = set()
            for name in self.list_mcp_names():
                for tool in self._tools_by_mcp.get(name, {}).values():
                    identity = id(tool)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    tools.append(tool)
            return tools
        if mcp_name in self._disabled_mcps:
            return []
        if mcp_name not in self._clients:
            return []
        tools: list[ITool] = []
        seen: set[int] = set()
        for tool in self._tools_by_mcp.get(mcp_name, {}).values():
            identity = id(tool)
            if identity in seen:
                continue
            seen.add(identity)
            tools.append(tool)
        return tools

    def get_tool(self, mcp_name: str, tool_name: str) -> ITool | None:
        """Get one tool by `mcp_name + tool_name`."""
        if mcp_name in self._disabled_mcps:
            return None
        tools = self._tools_by_mcp.get(mcp_name)
        if not tools:
            return None
        normalized_name = self._normalize_tool_name(mcp_name, tool_name)
        return tools.get(normalized_name)

    async def _refresh_mcp(self, mcp_name: str) -> None:
        client = self._clients[mcp_name]
        if mcp_name not in self._connected_mcps:
            await client.connect()
            self._connected_mcps.add(mcp_name)
        tools = await client.list_tools()
        mapping: dict[str, ITool] = {}
        for tool in tools:
            if not tool.name:
                continue
            short_name = self._normalize_tool_name(mcp_name, tool.name)
            mapping[short_name] = tool
            mapping[tool.name] = tool
        self._tools_by_mcp[mcp_name] = mapping

    def _ensure_known_mcp(self, mcp_name: str) -> None:
        if mcp_name not in self._clients:
            raise KeyError(f"unknown mcp: {mcp_name}")

    @staticmethod
    def _normalize_tool_name(mcp_name: str, tool_name: str) -> str:
        prefix = f"{mcp_name}:"
        if tool_name.startswith(prefix):
            return tool_name[len(prefix):]
        return tool_name


# Backward compatibility: existing call sites still import MCPToolProvider.
MCPToolProvider = McpToolManager


__all__ = ["McpToolManager", "MCPToolProvider"]
