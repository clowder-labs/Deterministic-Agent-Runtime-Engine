from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.interfaces import IMCPClient
from ..core.models import (
    Evidence,
    Resource,
    ResourceContent,
    RunContext,
    ToolDefinition,
    ToolResult,
    ToolRiskLevel,
    ToolType,
    new_id,
)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamable_http_client
except Exception:  # pragma: no cover - optional dependency
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None
    streamable_http_client = None


class MCPUnavailableError(RuntimeError):
    pass


@dataclass
class StdioMCPConfig:
    command: str
    args: list[str]
    env: dict[str, str] | None = None


@dataclass
class StreamableHTTPConfig:
    url: str


class BaseMCPClient(IMCPClient):
    def __init__(self, name: str) -> None:
        self._name = name
        self._session: ClientSession | None = None
        self._client_cm = None

    @property
    def name(self) -> str:
        return self._name

    async def connect(self) -> None:
        if ClientSession is None:
            raise MCPUnavailableError("mcp SDK is not installed")
        if self._session is not None:
            return
        await self._connect_session()

    async def disconnect(self) -> None:
        if self._session is None:
            return
        await self._session.__aexit__(None, None, None)
        self._session = None
        if self._client_cm is not None:
            await self._client_cm.__aexit__(None, None, None)
            self._client_cm = None

    async def list_tools(self) -> list[ToolDefinition]:
        session = await self._require_session()
        result = await session.list_tools()
        tools = getattr(result, "tools", [])
        return [
            ToolDefinition(
                name=getattr(tool, "name", ""),
                description=getattr(tool, "description", ""),
                input_schema=getattr(tool, "inputSchema", {}) or {},
                output_schema=getattr(tool, "outputSchema", {}) or {},
                tool_type=ToolType.ATOMIC,
                risk_level=ToolRiskLevel.READ_ONLY,
                requires_approval=False,
                timeout_seconds=30,
                produces_assertions=[],
                is_work_unit=False,
            )
            for tool in tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any], context: RunContext) -> ToolResult:
        session = await self._require_session()
        result = await session.call_tool(tool_name, arguments=arguments)
        is_error = getattr(result, "isError", False)
        structured = getattr(result, "structuredContent", None)
        content_blocks = getattr(result, "content", [])
        text_chunks = [getattr(block, "text", "") for block in content_blocks if hasattr(block, "text")]
        output = structured if structured is not None else {"content": text_chunks}
        evidence = [
            Evidence(
                evidence_id=new_id("evidence"),
                kind="mcp_result",
                payload=output or {},
            )
        ]
        return ToolResult(
            success=not is_error,
            output=output or {},
            error="mcp tool error" if is_error else None,
            evidence=evidence,
        )

    async def list_resources(self) -> list[Resource]:
        session = await self._require_session()
        result = await session.list_resources()
        resources = getattr(result, "resources", [])
        return [
            Resource(
                uri=str(getattr(resource, "uri", "")),
                name=getattr(resource, "name", ""),
                description=getattr(resource, "description", None),
                mime_type=getattr(resource, "mimeType", None),
            )
            for resource in resources
        ]

    async def read_resource(self, uri: str) -> ResourceContent:
        session = await self._require_session()
        result = await session.read_resource(uri)
        contents = getattr(result, "contents", [])
        if not contents:
            return ResourceContent(uri=uri, text=None, mime_type=None)
        content = contents[0]
        text = getattr(content, "text", None)
        mime_type = getattr(content, "mimeType", None)
        return ResourceContent(uri=uri, text=text, mime_type=mime_type)

    async def _require_session(self) -> ClientSession:
        if self._session is None:
            await self.connect()
        return self._session

    async def _connect_session(self) -> None:
        raise NotImplementedError


class StdioMCPClient(BaseMCPClient):
    def __init__(self, name: str, config: StdioMCPConfig) -> None:
        super().__init__(name)
        self._config = config

    @property
    def transport(self) -> str:
        return "stdio"

    async def _connect_session(self) -> None:
        params = StdioServerParameters(
            command=self._config.command,
            args=self._config.args,
            env=self._config.env or {},
        )
        self._client_cm = stdio_client(params)
        read, write = await self._client_cm.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()


class StreamableHTTPMCPClient(BaseMCPClient):
    def __init__(self, name: str, config: StreamableHTTPConfig) -> None:
        super().__init__(name)
        self._config = config

    @property
    def transport(self) -> str:
        return "streamable_http"

    async def _connect_session(self) -> None:
        self._client_cm = streamable_http_client(self._config.url)
        read, write, _ = await self._client_cm.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()
