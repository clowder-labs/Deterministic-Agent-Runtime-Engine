"""MCP (Model Context Protocol) client support for DARE Framework.

This package provides MCP client functionality for connecting to MCP servers
and exposing their tools to the DARE agent framework.

Key Components:
- MCPServerConfig: Configuration for a single MCP server
- IMCPClient: Stable client interface
- Transports: stdio, HTTP (Streamable HTTP)

Supported defaults live in `dare_framework.mcp.defaults`.

Typical Usage:
    from dare_framework.mcp.defaults import load_mcp_configs, create_mcp_clients, MCPToolProvider
    from dare_framework.tool.default_tool_manager import ToolManager

    # Load configurations from .dare/mcp directory
    configs = load_mcp_configs(workspace_dir="/path/to/project")

    # Create and connect clients
    clients = await create_mcp_clients(configs, connect=True)

    # Wrap as tool provider
    provider = MCPToolProvider(clients)
    await provider.initialize()

    # Register with tool manager
    tool_manager = ToolManager()
    tool_manager.register_provider(provider)

Or use the automatic integration via AgentBuilder:
    agent = (
        DareAgentBuilder("my_agent")
        .with_config(config)  # config.mcp_paths defines where to scan
        .build()
    )
    # MCP tools are automatically loaded and registered
"""

from dare_framework.mcp.kernel import IMCPClient
from dare_framework.mcp.manager import MCPManager
from dare_framework.mcp.types import MCPConfigFile, MCPServerConfig, TransportType

__all__ = [
    # Types
    "MCPConfigFile",
    "MCPServerConfig",
    "TransportType",
    "IMCPClient",
    "MCPManager",
]
