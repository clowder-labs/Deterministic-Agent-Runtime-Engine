"""MCP client components (Layer 2).

MCP connectivity is used by the Layer 1 `MCPAdapter`. Clients themselves are
treated as pluggable components so different transports/SDKs can be integrated.
"""

from dare_framework.components.mcp_clients.noop import NoOpMCPClient
from dare_framework.components.mcp_clients.protocols import IMCPClient

__all__ = [
    "IMCPClient",
    "NoOpMCPClient",
]

