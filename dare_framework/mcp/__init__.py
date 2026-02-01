"""MCP (Model Context Protocol) client support for DARE Framework.

This package provides MCP client functionality for connecting to MCP servers
and exposing their tools to the DARE agent framework.

Key Components:
- MCPServerConfig: Configuration for a single MCP server
- MCPConfigLoader: Scans directories for MCP configuration files
- MCPClient: High-level MCP client implementing IMCPClient
- MCPClientFactory: Creates clients from configuration
- Transports: stdio, HTTP (Streamable HTTP)

Typical Usage:
    from dare_framework.mcp import load_mcp_configs, create_mcp_clients
    from dare_framework.tool import MCPToolkit

    # Load configurations from .dare/mcp directory
    configs = load_mcp_configs(workspace_dir="/path/to/project")

    # Create and connect clients
    clients = await create_mcp_clients(configs, connect=True)

    # Wrap as tool provider
    toolkit = MCPToolkit(clients)
    await toolkit.initialize()

    # Register with agent
    for tool in toolkit.list_tools():
        tool_manager.register_tool(tool)

Or use the automatic integration via AgentBuilder:
    agent = (
        DareAgentBuilder("my_agent")
        .with_config(config)  # config.mcp_paths defines where to scan
        .build()
    )
    # MCP tools are automatically loaded and registered
"""

from dare_framework.mcp.client import MCPClient, MCPError
from dare_framework.mcp.factory import (
    MCPClientFactory,
    create_and_connect_mcp_clients,
    create_mcp_clients,
)
from dare_framework.mcp.loader import MCPConfigLoader, load_mcp_configs
from dare_framework.mcp.types import MCPConfigFile, MCPServerConfig, TransportType

__all__ = [
    # Types
    "MCPConfigFile",
    "MCPServerConfig",
    "TransportType",
    # Loader
    "MCPConfigLoader",
    "load_mcp_configs",
    # Client
    "MCPClient",
    "MCPError",
    # Factory
    "MCPClientFactory",
    "create_and_connect_mcp_clients",
    "create_mcp_clients",
]
