from __future__ import annotations

from typing import Any

import pytest

from dare_framework.mcp.client import MCPClient
from dare_framework.tool.types import RunContext


class _FakeTransport:
    def __init__(self) -> None:
        self._connected = False
        self._responses: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True

    async def send(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        if method == "initialize":
            self._responses.append(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "serverInfo": {"name": "fake-mcp", "version": "1.0.0"},
                        "capabilities": {"tools": {}},
                    },
                }
            )
            return
        if method == "tools/list":
            self._responses.append(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "tools": [
                            {
                                "name": "add",
                                "description": "Add two numbers.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                                    "required": ["a", "b"],
                                },
                                "timeout_seconds": 12,
                            }
                        ]
                    },
                }
            )
            return
        if method == "tools/call":
            self.tool_calls.append(dict(message.get("params", {})))
            self._responses.append(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "content": [{"type": "text", "text": "3"}],
                        "isError": False,
                    },
                }
            )
            return

    async def receive(self) -> dict[str, Any]:
        if not self._responses:
            raise RuntimeError("No queued response")
        return self._responses.pop(0)

    async def close(self) -> None:
        self._connected = False


@pytest.mark.asyncio
async def test_mcp_client_list_tools_returns_itool_and_executes_via_call_tool() -> None:
    transport = _FakeTransport()
    client = MCPClient("local_math", transport, transport_type="http")
    await client.connect()

    tools = await client.list_tools()

    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "local_math:add"
    assert tool.description == "Add two numbers."
    assert tool.input_schema["type"] == "object"
    assert tool.timeout_seconds == 12

    result = await tool.execute(run_context=RunContext(None), a=1, b=2)
    assert result.success is True
    assert transport.tool_calls == [{"name": "add", "arguments": {"a": 1, "b": 2}}]
