"""Base transport protocol for MCP communication.

All MCP transports implement this protocol, providing a unified interface
for sending and receiving JSON-RPC messages regardless of the underlying
transport mechanism (stdio, HTTP, gRPC).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ITransport(Protocol):
    """Protocol defining the MCP transport interface.

    A transport handles the low-level communication with an MCP server,
    abstracting away the details of how JSON-RPC messages are sent and received.

    The message format is always JSON-RPC 2.0, but the wire format varies:
    - stdio: newline-delimited JSON
    - HTTP: JSON body or SSE stream
    - gRPC: protobuf-wrapped JSON
    """

    @property
    def is_connected(self) -> bool:
        """Check if the transport is currently connected."""
        ...

    async def connect(self) -> None:
        """Establish the transport connection.

        For stdio: launch subprocess
        For HTTP: optionally establish SSE connection
        For gRPC: establish channel

        Raises:
            ConnectionError: If connection fails.
            TimeoutError: If connection times out.
        """
        ...

    async def send(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message to the server.

        Args:
            message: JSON-RPC request or notification.

        Raises:
            ConnectionError: If not connected or connection lost.
            IOError: If send fails.
        """
        ...

    async def receive(self) -> dict[str, Any]:
        """Receive the next JSON-RPC message from the server.

        This method blocks until a message is available or an error occurs.

        Returns:
            JSON-RPC response, result, or notification.

        Raises:
            ConnectionError: If connection lost.
            TimeoutError: If receive times out.
            IOError: If receive fails.
        """
        ...

    async def close(self) -> None:
        """Close the transport connection.

        For stdio: terminate subprocess
        For HTTP: close SSE connection
        For gRPC: close channel

        This method should be idempotent and not raise on double-close.
        """
        ...


__all__ = ["ITransport"]
