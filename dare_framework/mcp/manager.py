"""MCP lifecycle manager.

This module keeps MCP-specific lifecycle concerns separate from the generic
tool registry (`ToolManager`).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

from dare_framework.config.types import Config
from dare_framework.tool.kernel import IToolManager, IToolProvider
from dare_framework.tool.types import ToolDefinition

logger = logging.getLogger(__name__)

LoadConfigsFn = Callable[..., list[Any]]
CreateClientsFn = Callable[..., Awaitable[list[Any]]]
ProviderFactoryFn = Callable[[list[Any]], IToolProvider]


class MCPManager:
    """Manage MCP provider lifecycle and runtime registry integration."""

    def __init__(
        self,
        config: Config,
        *,
        provider: IToolProvider | None = None,
        load_configs: LoadConfigsFn | None = None,
        create_clients: CreateClientsFn | None = None,
        provider_factory: ProviderFactoryFn | None = None,
    ) -> None:
        if config is None:
            raise ValueError("MCPManager requires a non-null Config.")

        if load_configs is None or create_clients is None or provider_factory is None:
            from dare_framework.mcp.defaults import MCPToolProvider, create_mcp_clients, load_mcp_configs

            load_configs = load_configs or load_mcp_configs
            create_clients = create_clients or create_mcp_clients
            provider_factory = provider_factory or MCPToolProvider

        self._config = config
        self._provider = provider
        self._load_configs = load_configs
        self._create_clients = create_clients
        self._provider_factory = provider_factory

    @property
    def config(self) -> Config:
        return self._config

    @property
    def provider(self) -> IToolProvider | None:
        return self._provider

    def update_config(self, config: Config) -> None:
        if config is None:
            raise ValueError("MCPManager requires a non-null Config.")
        self._config = config

    async def load_provider(
        self,
        *,
        paths: list[str | Path] | None = None,
    ) -> IToolProvider:
        scan_paths = list(paths) if paths is not None else (list(self._config.mcp_paths) or None)

        mcp_configs = self._load_configs(
            paths=scan_paths,
            workspace_dir=self._config.workspace_dir,
            user_dir=self._config.user_dir,
        )

        allowed_mcps = getattr(self._config, "allow_mcps", None)
        if allowed_mcps is None:
            # Backward compatibility for legacy config field name.
            allowed_mcps = getattr(self._config, "allowmcps", None)
        if allowed_mcps:
            allowed = set(allowed_mcps)
            mcp_configs = [item for item in mcp_configs if getattr(item, "name", None) in allowed]

        clients = await self._create_clients(mcp_configs, connect=True, skip_errors=True)
        provider = self._provider_factory(clients)
        await _initialize_provider(provider)

        logger.info(
            "MCP tool provider loaded: %s servers, %s tools",
            len(clients),
            len(provider.list_tools()),
        )
        return provider

    async def reload(
        self,
        tool_manager: IToolManager,
        *,
        config: Config | None = None,
        paths: list[str | Path] | None = None,
    ) -> IToolProvider:
        if config is not None:
            self.update_config(config)

        new_provider = await self.load_provider(paths=paths)
        old_provider = self._provider
        if old_provider is not None:
            tool_manager.unregister_provider(old_provider)

        try:
            tool_manager.register_provider(new_provider)
            await tool_manager.refresh()
        except Exception:
            await _close_provider(new_provider)
            if old_provider is not None:
                tool_manager.register_provider(old_provider)
                await tool_manager.refresh()
            raise

        if old_provider is not None:
            await _close_provider(old_provider)
        self._provider = new_provider
        return new_provider

    async def unload(self, tool_manager: IToolManager) -> bool:
        if self._provider is None:
            return False

        provider = self._provider
        removed = tool_manager.unregister_provider(provider)
        await tool_manager.refresh()
        await _close_provider(provider)
        self._provider = None
        return removed

    def list_mcp_tool_defs(
        self,
        tool_manager: IToolManager,
        *,
        tool_name: str | None = None,
    ) -> list[ToolDefinition]:
        mcp_tool_defs: list[ToolDefinition] = []
        for tool_def in tool_manager.list_tool_defs():
            function = tool_def.get("function")
            if not isinstance(function, dict):
                continue
            name = function.get("name")
            if not isinstance(name, str) or ":" not in name:
                continue
            if tool_name is not None and name != tool_name:
                continue
            mcp_tool_defs.append(tool_def)
        return mcp_tool_defs


async def _initialize_provider(provider: Any) -> None:
    initialize = getattr(provider, "initialize", None)
    if not callable(initialize):
        return
    maybe_coro = initialize()
    if asyncio.iscoroutine(maybe_coro):
        await maybe_coro


async def _close_provider(provider: Any) -> None:
    close_method = getattr(provider, "close", None)
    if not callable(close_method):
        return
    maybe_coro = close_method()
    if asyncio.iscoroutine(maybe_coro):
        await maybe_coro


__all__ = ["MCPManager"]
