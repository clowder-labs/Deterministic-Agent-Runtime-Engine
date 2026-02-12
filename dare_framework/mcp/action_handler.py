"""MCP-domain deterministic action handlers."""

from __future__ import annotations

from typing import Any, Protocol

from dare_framework.config.kernel import IConfigProvider
from dare_framework.config.types import Config
from dare_framework.tool.kernel import ITool
from dare_framework.transport.interaction.handlers import IActionHandler
from dare_framework.transport.interaction.resource_action import ResourceAction


class IMcpCatalog(Protocol):
    """Minimal MCP tool manager contract required by interaction actions."""

    def list_mcp_names(self, *, include_disabled: bool = False) -> list[str]:
        ...

    def list_tools(self, mcp_name: str | None = None) -> list[ITool]:
        ...

    def get_tool(self, mcp_name: str, tool_name: str) -> ITool | None:
        ...

    async def reload(self, mcp_name: str | None = None) -> None:
        ...


class McpActionHandler(IActionHandler):
    """Handle deterministic mcp-domain actions."""

    def __init__(
        self,
        *,
        config: Config | None,
        manager: IConfigProvider | None,
        mcp_manager: IMcpCatalog | None = None,
    ) -> None:
        self._config = config
        self._config_manager = manager
        self._mcp_manager = mcp_manager

    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.MCP_LIST, ResourceAction.MCP_RELOAD, ResourceAction.MCP_SHOW_TOOL}

    # noinspection PyMethodOverriding
    async def invoke(
        self,
        action: ResourceAction,
        **params: Any,
    ) -> Any:
        if action == ResourceAction.MCP_RELOAD:
            return await self._reload(**params)
        if action == ResourceAction.MCP_SHOW_TOOL:
            return self._show_tool(**params)
        if action == ResourceAction.MCP_LIST:
            return self._mcp_list(**params)
        raise ValueError(f"unsupported mcp action: {action.value}")

    def _resolve_config(self) -> Config:
        if self._config is not None:
            return self._config
        if self._config_manager is not None:
            return self._config_manager.current()
        raise RuntimeError("mcp action handler requires config or config provider")

    def _mcp_list(
        self,
        *,
        mcp_name: str | None = None,
        mcp: str | None = None,
        **_params: Any,
    ) -> dict[str, Any]:
        cfg = self._resolve_config()
        manager = self._mcp_manager
        resolved_mcp_name = _first_non_empty(mcp_name, mcp)
        tools: list[dict[str, Any]] = []
        if manager is not None:
            for tool in manager.list_tools(mcp_name=resolved_mcp_name):
                tools.append(_tool_to_dict(tool))
            mcps = manager.list_mcp_names()
        else:
            mcps = sorted((getattr(cfg, "mcp", None) or {}).keys())

        return {
            "mcps": mcps,
            "mcp_paths": list(getattr(cfg, "mcp_paths", []) or []),
            "tools": tools,
        }

    async def _reload(
        self,
        *,
        mcp_name: str | None = None,
        mcp: str | None = None,
        **_params: Any,
    ) -> dict[str, Any]:
        if self._mcp_manager is None:
            raise RuntimeError("mcp action handler requires mcp manager for mcp:reload")
        resolved_mcp_name = _first_non_empty(mcp_name, mcp)
        await self._mcp_manager.reload(resolved_mcp_name)
        return {"ok": True, "reloaded": resolved_mcp_name if resolved_mcp_name is not None else "all"}

    def _show_tool(
        self,
        *,
        mcp_name: str | None = None,
        mcp: str | None = None,
        tool_name: str | None = None,
        tool: str | None = None,
        **_params: Any,
    ) -> dict[str, Any]:
        if self._mcp_manager is None:
            raise RuntimeError("mcp action handler requires mcp manager for mcp:show-tool")
        resolved_mcp_name = _first_non_empty(mcp_name, mcp)
        resolved_tool_name = _first_non_empty(tool_name, tool)
        if not resolved_mcp_name or not resolved_tool_name:
            raise ValueError("mcp:show-tool requires mcp_name and tool_name")
        tool = self._mcp_manager.get_tool(resolved_mcp_name, resolved_tool_name)
        if tool is None:
            return {"found": False, "mcp_name": resolved_mcp_name, "tool_name": resolved_tool_name}
        return {"found": True, "tool": _tool_to_dict(tool)}


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
    return None


def _tool_to_dict(tool: ITool) -> dict[str, Any]:
    capability_kind = getattr(tool, "capability_kind", None)
    if hasattr(capability_kind, "value"):
        capability_kind = capability_kind.value
    return {
        "name": getattr(tool, "name", ""),
        "description": getattr(tool, "description", ""),
        "input_schema": getattr(tool, "input_schema", {}),
        "output_schema": getattr(tool, "output_schema", {}),
        "requires_approval": getattr(tool, "requires_approval", False),
        "risk_level": getattr(tool, "risk_level", "read_only"),
        "timeout_seconds": getattr(tool, "timeout_seconds", 30),
        "is_work_unit": getattr(tool, "is_work_unit", False),
        "capability_kind": capability_kind,
    }


__all__ = ["IMcpCatalog", "McpActionHandler"]
