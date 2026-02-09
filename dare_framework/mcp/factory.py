"""MCP client factory.

Creates IMCPClient instances from MCPServerConfig based on transport type.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dare_framework.mcp.client import MCPClient
from dare_framework.mcp.kernel import IMCPClient
from dare_framework.mcp.transports.http import HTTPTransport
from dare_framework.mcp.transports.stdio import StdioTransport
from dare_framework.mcp.types import MCPServerConfig, TransportType

if TYPE_CHECKING:
    from dare_framework.mcp.transports.base import ITransport

logger = logging.getLogger(__name__)


class MCPClientFactory:
    """Factory for creating MCP clients from configuration.

    Creates the appropriate transport based on the configuration and
    wraps it in an MCPClient.

    Example:
        factory = MCPClientFactory()
        configs = load_mcp_configs()

        clients = []
        for config in configs:
            client = factory.create(config)
            clients.append(client)
    """

    def create(self, config: MCPServerConfig) -> IMCPClient:
        """Create an MCP client from configuration.

        Args:
            config: MCP server configuration.

        Returns:
            IMCPClient instance (not yet connected).

        Raises:
            ValueError: If transport type is not supported.
        """
        transport = self._create_transport(config)
        client = MCPClient(
            name=config.name,
            transport=transport,
            transport_type=config.transport.value,
        )
        return client

    def _create_transport(self, config: MCPServerConfig) -> ITransport:
        """Create transport based on configuration.

        Args:
            config: MCP server configuration.

        Returns:
            Transport instance.

        Raises:
            ValueError: If transport type is not supported.
        """
        if config.transport == TransportType.STDIO:
            return self._create_stdio_transport(config)
        elif config.transport == TransportType.HTTP:
            return self._create_http_transport(config)
        elif config.transport == TransportType.GRPC:
            raise ValueError(
                f"gRPC transport not yet implemented for MCP server '{config.name}'. "
                "Use stdio or http transport instead."
            )
        else:
            raise ValueError(f"Unknown transport type: {config.transport}")

    def _create_stdio_transport(self, config: MCPServerConfig) -> StdioTransport:
        """Create stdio transport."""
        if not config.command:
            raise ValueError(
                f"MCP server '{config.name}' requires 'command' for stdio transport"
            )

        return StdioTransport(
            command=config.command,
            env=config.env or None,
            timeout_seconds=config.timeout_seconds,
            cwd=config.cwd,
        )

    def _create_http_transport(self, config: MCPServerConfig) -> HTTPTransport:
        """Create HTTP transport."""
        if not config.url:
            raise ValueError(
                f"MCP server '{config.name}' requires 'url' for http transport"
            )

        # 默认关闭 SSE 通知通道，仅用 POST 请求/响应；多数简单 MCP 服务只支持 POST
        return HTTPTransport(
            url=config.url,
            headers=config.headers or None,
            timeout_seconds=config.timeout_seconds,
            enable_notifications=False,
        )


async def create_mcp_clients(
    configs: list[MCPServerConfig],
    *,
    connect: bool = False,
    skip_errors: bool = True,
) -> list[IMCPClient]:
    """Create MCP clients from a list of configurations.

    This is a convenience function that creates clients using MCPClientFactory.

    Args:
        configs: List of MCP server configurations.
        connect: Whether to connect each client after creation.
        skip_errors: Whether to skip clients that fail to create/connect.
                    If False, raises on first error.

    Returns:
        List of IMCPClient instances.
    """
    factory = MCPClientFactory()
    clients: list[IMCPClient] = []

    for config in configs:
        if not config.enabled:
            logger.debug(f"Skipping disabled MCP server: {config.name}")
            continue

        try:
            client = factory.create(config)

            if connect:
                await client.connect()
                logger.info(f"Connected to MCP server: {config.name}")

            clients.append(client)

        except Exception as e:
            if skip_errors:
                logger.warning(f"Failed to create MCP client '{config.name}': {e}")
            else:
                raise

    return clients


async def create_and_connect_mcp_clients(
    configs: list[MCPServerConfig],
) -> list[IMCPClient]:
    """Create and connect MCP clients.

    Convenience wrapper that creates clients and connects them,
    skipping any that fail.

    Args:
        configs: List of MCP server configurations.

    Returns:
        List of connected IMCPClient instances.
    """
    return await create_mcp_clients(configs, connect=True, skip_errors=True)


__all__ = [
    "MCPClientFactory",
    "create_and_connect_mcp_clients",
    "create_mcp_clients",
]
