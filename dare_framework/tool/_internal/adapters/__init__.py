"""Protocol adapter implementations for the tool domain."""

from dare_framework.tool._internal.adapters.mcp_adapter import MCPAdapter
from dare_framework.tool._internal.adapters.noop_mcp_client import NoOpMCPClient

__all__ = ["MCPAdapter", "NoOpMCPClient"]
