"""MCP client implementation.

The MCPClient wraps a transport and provides high-level MCP protocol
operations (initialize, list_tools, call_tool, etc.) using JSON-RPC 2.0.
"""

from __future__ import annotations

import logging
from typing import Any

from dare_framework.mcp.kernel import IMCPClient
from dare_framework.mcp.transports.base import ITransport
from dare_framework.tool.kernel import ITool
from dare_framework.tool.types import (
    CapabilityKind,
    RiskLevelName,
    RunContext,
    ToolResult,
    ToolType,
)

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Error returned by MCP server."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")


class MCPClient(IMCPClient):
    """High-level MCP client implementing the IMCPClient interface.

    Wraps a transport (stdio, HTTP, etc.) and provides MCP protocol operations.
    Handles JSON-RPC request/response correlation and error handling.

    Example:
        transport = StdioTransport(command=["mcp-server-fs"])
        client = MCPClient("filesystem", transport)
        await client.connect()

        tools = await client.list_tools()
        result = await client.call_tool("read_file", {"path": "/tmp/test.txt"})

        await client.disconnect()
    """

    # MCP protocol version
    PROTOCOL_VERSION = "2024-11-05"

    def __init__(
        self,
        name: str,
        transport: ITransport,
        *,
        transport_type: str = "unknown",
    ) -> None:
        """Initialize MCP client.

        Args:
            name: Unique name for this MCP client.
            transport: Transport instance for communication.
            transport_type: Transport type string (for metadata).
        """
        self._name = name
        self._transport = transport
        self._transport_type = transport_type
        self._request_id = 0
        self._initialized = False

        # Server capabilities (populated after initialize)
        self._server_info: dict[str, Any] = {}
        self._capabilities: dict[str, Any] = {}

    @property
    def name(self) -> str:
        """Return the client name."""
        return self._name

    @property
    def transport(self) -> str:
        """Return the transport type."""
        return self._transport_type

    @property
    def server_info(self) -> dict[str, Any]:
        """Return server information from initialization."""
        return self._server_info

    @property
    def capabilities(self) -> dict[str, Any]:
        """Return server capabilities from initialization."""
        return self._capabilities

    async def connect(self) -> None:
        """Connect to the MCP server and perform initialization handshake.

        The MCP protocol requires an initialize/initialized exchange before
        other operations.

        Raises:
            ConnectionError: If connection or initialization fails.
        """
        await self._transport.connect()

        try:
            # Send initialize request
            init_response = await self._request(
                "initialize",
                {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "capabilities": {
                        "roots": {"listChanged": True},
                    },
                    "clientInfo": {
                        "name": "dare-framework",
                        "version": "0.1.0",
                    },
                },
            )

            # Store server info and capabilities
            self._server_info = init_response.get("serverInfo", {})
            self._capabilities = init_response.get("capabilities", {})

            logger.info(
                f"MCP server initialized: {self._server_info.get('name', 'unknown')} "
                f"v{self._server_info.get('version', '?')}"
            )

            # Send initialized notification (no response expected)
            await self._notify("notifications/initialized", {})

            self._initialized = True

        except Exception as e:
            await self._transport.close()
            raise ConnectionError(f"MCP initialization failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        self._initialized = False
        await self._transport.close()
        logger.info(f"MCP client '{self._name}' disconnected")

    async def list_tools(self) -> list[ITool]:
        """List available tools from the MCP server.

        Returns:
            List of framework-native tool adapters.

        Raises:
            MCPError: If the server returns an error.
            ConnectionError: If not connected.
        """
        self._ensure_initialized()

        response = await self._request("tools/list", {})
        tool_defs = response.get("tools", [])
        tools: list[ITool] = []

        for tool_def in tool_defs:
            tool_name = _tool_field(tool_def, "name", "")
            if not tool_name:
                continue
            full_name = f"{self._name}:{tool_name}"
            tools.append(
                _MCPRemoteTool(
                    client=self,
                    tool_def=tool_def,
                    tool_name=str(tool_name),
                    full_name=full_name,
                )
            )

        logger.debug(f"MCP server '{self._name}' has {len(tools)} tools")
        return tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: RunContext[Any] | None = None,
    ) -> ToolResult:
        """Invoke a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call.
            arguments: Tool input arguments.
            context: Optional run context (for metadata, not used by MCP).

        Returns:
            ToolResult with success status and output.

        Raises:
            MCPError: If the server returns an error.
            ConnectionError: If not connected.
        """
        self._ensure_initialized()

        try:
            response = await self._request(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": arguments,
                },
            )

            # Parse MCP tool result format
            content = response.get("content", [])
            is_error = response.get("isError", False)

            # Extract text content (MCP returns content as array)
            output_text = ""
            output_data: dict[str, Any] = {}

            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    if item_type == "text":
                        output_text += item.get("text", "")
                    elif item_type == "image":
                        output_data["image"] = item
                    elif item_type == "resource":
                        output_data["resource"] = item

            if is_error:
                return ToolResult(
                    success=False,
                    output={"text": output_text, **output_data},
                    error=output_text or "Tool execution failed",
                    evidence=[],
                )

            return ToolResult(
                success=True,
                output={"text": output_text, **output_data} if output_data else output_text,
                error=None,
                evidence=[],
            )

        except MCPError as e:
            return ToolResult(
                success=False,
                output={},
                error=str(e),
                evidence=[],
            )

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources from the MCP server.

        Returns:
            List of resource definitions.

        Raises:
            MCPError: If the server returns an error or doesn't support resources.
        """
        self._ensure_initialized()

        if not self._capabilities.get("resources"):
            return []

        response = await self._request("resources/list", {})
        return response.get("resources", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource by URI.

        Args:
            uri: Resource URI.

        Returns:
            Resource content.

        Raises:
            MCPError: If the server returns an error.
        """
        self._ensure_initialized()

        response = await self._request("resources/read", {"uri": uri})
        return response

    async def list_prompts(self) -> list[dict[str, Any]]:
        """List available prompts from the MCP server.

        Returns:
            List of prompt definitions.

        Raises:
            MCPError: If the server returns an error or doesn't support prompts.
        """
        self._ensure_initialized()

        if not self._capabilities.get("prompts"):
            return []

        response = await self._request("prompts/list", {})
        return response.get("prompts", [])

    def _ensure_initialized(self) -> None:
        """Ensure the client is connected and initialized."""
        if not self._initialized:
            raise ConnectionError(
                f"MCP client '{self._name}' not initialized. Call connect() first."
            )

    async def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for response.

        Args:
            method: RPC method name.
            params: Method parameters.

        Returns:
            Response result.

        Raises:
            MCPError: If server returns an error response.
        """
        self._request_id += 1
        request_id = self._request_id

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        await self._transport.send(message)

        # Wait for response with matching ID
        # Note: This simple implementation assumes responses arrive in order.
        # A more robust implementation would track pending requests.
        while True:
            response = await self._transport.receive()

            # Check if this is a response to our request
            if response.get("id") == request_id:
                if "error" in response:
                    error = response["error"]
                    raise MCPError(
                        code=error.get("code", -1),
                        message=error.get("message", "Unknown error"),
                        data=error.get("data"),
                    )
                return response.get("result", {})

            # If it's a notification, log and continue waiting
            if "method" in response and "id" not in response:
                logger.debug(f"Received notification: {response.get('method')}")
                continue

            # Unexpected response - log warning
            logger.warning(f"Unexpected response: {response}")

    async def _notify(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected).

        Args:
            method: Notification method name.
            params: Notification parameters.
        """
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        await self._transport.send(message)


class _MCPRemoteTool(ITool):
    """Adapter that turns MCP tool definitions into ITool implementations."""

    def __init__(
        self,
        *,
        client: MCPClient,
        tool_def: Any,
        tool_name: str,
        full_name: str,
    ) -> None:
        self._client = client
        self._tool_def = tool_def
        self._tool_name = tool_name
        self._full_name = full_name

    @property
    def name(self) -> str:
        return self._full_name

    @property
    def description(self) -> str:
        return str(_tool_field(self._tool_def, "description", ""))

    @property
    def input_schema(self) -> dict[str, Any]:
        value = _tool_field(self._tool_def, "input_schema", {}, aliases=("inputSchema",))
        return dict(value) if isinstance(value, dict) else {}

    @property
    def output_schema(self) -> dict[str, Any]:
        value = _tool_field(self._tool_def, "output_schema", {}, aliases=("outputSchema",))
        return dict(value) if isinstance(value, dict) else {}

    @property
    def tool_type(self) -> ToolType:
        return ToolType.WORK_UNIT if self.is_work_unit else ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        value = _tool_field(self._tool_def, "risk_level", "read_only")
        return _normalize_risk_level(value)

    @property
    def requires_approval(self) -> bool:
        return bool(_tool_field(self._tool_def, "requires_approval", False))

    @property
    def timeout_seconds(self) -> int:
        value = _tool_field(self._tool_def, "timeout_seconds", 30)
        if isinstance(value, bool):
            return 30
        try:
            parsed = int(value)
        except (OverflowError, TypeError, ValueError):
            return 30
        return parsed if parsed > 0 else 30

    @property
    def is_work_unit(self) -> bool:
        return bool(_tool_field(self._tool_def, "is_work_unit", False))

    @property
    def capability_kind(self) -> CapabilityKind:
        value = _tool_field(self._tool_def, "capability_kind", CapabilityKind.TOOL)
        return _normalize_capability_kind(value)

    # noinspection PyMethodOverriding
    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        **params: Any,
    ) -> ToolResult:
        """Forward keyword parameters to remote MCP tool invocation."""
        return await self._client.call_tool(self._tool_name, params, context=run_context)


def _tool_field(
    tool_def: Any,
    field: str,
    default: Any,
    *,
    aliases: tuple[str, ...] = (),
) -> Any:
    if isinstance(tool_def, dict):
        if field in tool_def:
            return tool_def[field]
        for alias in aliases:
            if alias in tool_def:
                return tool_def[alias]
        return default
    if hasattr(tool_def, field):
        return getattr(tool_def, field)
    for alias in aliases:
        if hasattr(tool_def, alias):
            return getattr(tool_def, alias)
    return default


def _normalize_risk_level(value: Any) -> RiskLevelName:
    if hasattr(value, "value"):
        value = value.value
    return str(value)


def _normalize_capability_kind(value: Any) -> CapabilityKind:
    if isinstance(value, CapabilityKind):
        return value
    if hasattr(value, "value"):
        value = value.value
    try:
        return CapabilityKind(str(value))
    except ValueError:
        return CapabilityKind.TOOL


__all__ = ["MCPClient", "MCPError"]
