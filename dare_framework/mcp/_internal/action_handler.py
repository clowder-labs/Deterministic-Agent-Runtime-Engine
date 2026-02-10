"""MCP-domain deterministic action handlers."""

from __future__ import annotations

from typing import Any

from dare_framework.config.kernel import IConfigProvider
from dare_framework.config.types import Config
from dare_framework.transport.interaction.resource_action import ResourceAction
from dare_framework.transport.interaction.handlers import IActionHandler


class McpActionHandler(IActionHandler):
    """Handle deterministic mcp-domain actions."""

    def __init__(
        self,
        *,
        config: Config | None,
        manager: IConfigProvider | None,
    ) -> None:
        self._config = config
        self._config_manager = manager

    def supports(self) -> set[ResourceAction]:
        return {ResourceAction.MCP_LIST}

    async def invoke(
        self,
        action: ResourceAction,
        _params: dict[str, Any],
    ) -> Any:
        if action != ResourceAction.MCP_LIST:
            raise ValueError(f"unsupported mcp action: {action.value}")
        cfg = self._resolve_config()
        return {
            "mcps": sorted((getattr(cfg, "mcp", None) or {}).keys()),
            "mcp_paths": list(getattr(cfg, "mcp_paths", []) or []),
        }

    def _resolve_config(self) -> Config:
        if self._config is not None:
            return self._config
        if self._config_manager is not None:
            return self._config_manager.current()
        raise RuntimeError("mcp action handler requires config or config provider")


__all__ = ["McpActionHandler"]
