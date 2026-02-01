"""MCP transport implementations.

This package provides transport layer implementations for MCP communication:
- StdioTransport: Local subprocess via stdin/stdout
- HTTPTransport: Remote server via Streamable HTTP (HTTP + SSE)
- GRPCTransport: Remote server via gRPC (optional extension)
"""

from dare_framework.mcp.transports.base import ITransport
from dare_framework.mcp.transports.http import HTTPTransport
from dare_framework.mcp.transports.stdio import StdioTransport

__all__ = [
    "HTTPTransport",
    "ITransport",
    "StdioTransport",
]
