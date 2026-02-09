"""Streamable HTTP transport for MCP communication.

The HTTP transport connects to a remote MCP server using Streamable HTTP
(MCP spec 2025-03-26). It supports:
- POST requests with JSON responses for quick operations
- POST requests with SSE streaming for long-running operations
- Optional GET SSE connection for server-initiated notifications

This replaces the older HTTP+SSE transport (deprecated in 2024-11-05 spec).
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
from typing import Any, AsyncIterator
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _is_loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    normalized = hostname.strip().lower().strip("[]")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _should_trust_env(url: str) -> bool:
    """Return False for loopback endpoints so local MCP traffic bypasses proxies."""
    parsed = urlparse(url)
    return not _is_loopback_host(parsed.hostname)


class HTTPTransport:
    """MCP transport using Streamable HTTP.

    Implements the MCP Streamable HTTP transport specification (2025-03-26).
    Uses HTTP POST for requests and can handle both JSON and SSE responses.

    Example:
        transport = HTTPTransport(
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer xxx"},
        )
        await transport.connect()
        await transport.send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        response = await transport.receive()
        await transport.close()
    """

    def __init__(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout_seconds: int = 30,
        enable_notifications: bool = True,
    ) -> None:
        """Initialize HTTP transport.

        Args:
            url: MCP server endpoint URL.
            headers: Additional HTTP headers (e.g., for authentication).
            timeout_seconds: Timeout for HTTP requests in seconds.
            enable_notifications: Whether to establish SSE notification channel.
        """
        if not url:
            raise ValueError("url cannot be empty")

        self._url = url
        self._headers = dict(headers) if headers else {}
        self._timeout = timeout_seconds
        self._enable_notifications = enable_notifications
        # Local MCP services should not be routed through system HTTP proxies.
        self._trust_env = _should_trust_env(url)

        self._connected = False
        self._session_id: str | None = None
        self._client: Any = None  # httpx.AsyncClient
        self._notification_task: asyncio.Task[None] | None = None
        self._notification_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        # Pending request tracking for matching responses
        self._pending_requests: dict[int | str, asyncio.Future[dict[str, Any]]] = {}
        self._current_stream: AsyncIterator[dict[str, Any]] | None = None

    @property
    def is_connected(self) -> bool:
        """Check if connected to the server."""
        return self._connected

    async def connect(self) -> None:
        """Establish HTTP connection.

        Optionally starts SSE notification listener if enabled.

        Raises:
            ConnectionError: If connection fails.
            ImportError: If httpx is not installed.
        """
        if self._connected:
            return

        try:
            import httpx
        except ImportError as e:
            raise ImportError(
                "httpx is required for HTTP transport. "
                "Install it with: pip install httpx"
            ) from e

        try:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                trust_env=self._trust_env,
                headers={
                    **self._headers,
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            self._connected = True
            logger.info(f"HTTP transport connected to {self._url}")

            # Start notification listener if enabled
            if self._enable_notifications:
                self._notification_task = asyncio.create_task(
                    self._listen_notifications()
                )

        except Exception as e:
            raise ConnectionError(f"Failed to connect to MCP server: {e}") from e

    async def send(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message via HTTP POST.

        The response is queued internally and retrieved via receive().

        Args:
            message: JSON-RPC message to send.

        Raises:
            ConnectionError: If not connected.
            IOError: If request fails.
        """
        if not self._connected or self._client is None:
            raise ConnectionError("Not connected to MCP server")

        request_id = message.get("id")

        try:
            headers = {}
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id

            response = await self._client.post(
                self._url,
                json=message,
                headers=headers,
            )
            response.raise_for_status()

            # Check response content type
            content_type = response.headers.get("content-type", "")

            if "text/event-stream" in content_type:
                # SSE streaming response - parse and queue messages
                self._current_stream = self._parse_sse_response(response)
            else:
                # JSON response - queue only if it's a valid JSON-RPC message
                result = response.json()

                # Capture session ID if provided
                session_id = response.headers.get("mcp-session-id")
                if session_id:
                    self._session_id = session_id

                # Skip empty or non-JSON-RPC responses (e.g. server returns {} for notifications)
                if isinstance(result, dict) and ("id" in result or "method" in result):
                    await self._notification_queue.put(result)

            logger.debug(f"Sent: {message.get('method', request_id)}")

        except Exception as e:
            err_msg = str(e).strip() or getattr(e, "message", "") or type(e).__name__
            raise IOError(f"Failed to send message: {err_msg}") from e

    async def receive(self) -> dict[str, Any]:
        """Receive the next JSON-RPC message.

        Returns messages from either:
        - POST response (JSON or SSE stream)
        - GET SSE notification channel

        Returns:
            Parsed JSON-RPC message.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If receive times out.
        """
        if not self._connected:
            raise ConnectionError("Not connected to MCP server")

        # If we have an active stream, get next message from it
        if self._current_stream is not None:
            try:
                message = await self._current_stream.__anext__()
                # Check if this is the final response (has id)
                if "id" in message and "result" in message or "error" in message:
                    self._current_stream = None
                return message
            except StopAsyncIteration:
                self._current_stream = None

        # Otherwise get from notification queue
        try:
            message = await asyncio.wait_for(
                self._notification_queue.get(),
                timeout=self._timeout,
            )
            logger.debug(f"Received: {message.get('method', message.get('id', '?'))}")
            return message
        except asyncio.TimeoutError:
            raise TimeoutError(f"Receive timeout after {self._timeout}s")

    async def close(self) -> None:
        """Close the HTTP connection.

        This method is idempotent - safe to call multiple times.
        """
        if not self._connected:
            return

        self._connected = False

        # Cancel notification task
        if self._notification_task is not None:
            self._notification_task.cancel()
            try:
                await self._notification_task
            except asyncio.CancelledError:
                pass
            self._notification_task = None

        # Close HTTP client
        if self._client is not None:
            await self._client.aclose()
            self._client = None

        logger.info("HTTP transport closed")

    async def _parse_sse_response(
        self, response: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """Parse SSE stream from HTTP response.

        Args:
            response: httpx Response object.

        Yields:
            Parsed JSON-RPC messages from SSE events.
        """
        buffer = ""

        async for chunk in response.aiter_text():
            buffer += chunk

            # Process complete events
            while "\n\n" in buffer:
                event_text, buffer = buffer.split("\n\n", 1)

                # Parse SSE event
                data_lines = []
                for line in event_text.split("\n"):
                    if line.startswith("data:"):
                        data_lines.append(line[5:].strip())

                if data_lines:
                    data = "\n".join(data_lines)
                    try:
                        message = json.loads(data)
                        yield message
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in SSE event: {e}")

    async def _listen_notifications(self) -> None:
        """Background task to listen for server notifications via GET SSE.

        This establishes a long-lived SSE connection for server-initiated
        messages (e.g., tools/list_changed notifications).
        """
        if self._client is None:
            return

        try:
            headers = {"Accept": "text/event-stream"}
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id

            async with self._client.stream(
                "GET",
                self._url,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    logger.warning(
                        f"SSE notification channel returned {response.status_code}"
                    )
                    return

                async for message in self._parse_sse_response(response):
                    await self._notification_queue.put(message)

        except asyncio.CancelledError:
            logger.debug("Notification listener cancelled")
        except Exception as e:
            logger.warning(f"Notification listener error: {e}")


__all__ = ["HTTPTransport"]
