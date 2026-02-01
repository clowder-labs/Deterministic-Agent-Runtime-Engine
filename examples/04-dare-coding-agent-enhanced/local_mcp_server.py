#!/usr/bin/env python3
"""本地 MCP 服务：提供四则运算工具（加、减、乘、除）。

一个 MCP 服务暴露多个 tool，用于验证「一个服务提供多个 tool」的能力。

以 HTTP 方式对外提供 MCP 协议，需**先单独启动**本进程，再启动 Agent/CLI 连接。

用法：
  终端 1：python local_mcp_server.py          # 服务默认监听 http://127.0.0.1:8765
  终端 2：cd examples/04-dare-coding-agent-enhanced && python main.py   # CLI 连接该服务
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

_NUM_SCHEMA = {
    "type": "object",
    "properties": {
        "a": {"type": "number", "description": "第一个数"},
        "b": {"type": "number", "description": "第二个数"},
    },
    "required": ["a", "b"],
}

TOOLS_LIST = [
    {
        "name": "add",
        "description": "两数相加，返回和。",
        "inputSchema": _NUM_SCHEMA,
    },
    {
        "name": "subtract",
        "description": "两数相减，返回 a - b。",
        "inputSchema": _NUM_SCHEMA,
    },
    {
        "name": "multiply",
        "description": "两数相乘，返回积。",
        "inputSchema": _NUM_SCHEMA,
    },
    {
        "name": "divide",
        "description": "两数相除，返回 a / b。b 为 0 时返回错误。",
        "inputSchema": _NUM_SCHEMA,
    },
]


def _parse_two_numbers(arguments: dict[str, Any]) -> tuple[float, float]:
    a = float(arguments.get("a", 0))
    b = float(arguments.get("b", 0))
    return a, b


def handle_request(method: str, req_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    """处理单条 JSON-RPC 请求，返回 result 或 error。"""
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "local-math-server", "version": "0.2.0"},
        }

    if method == "tools/list":
        return {"tools": TOOLS_LIST}

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            a, b = _parse_two_numbers(arguments)
        except (TypeError, ValueError) as e:
            return {
                "content": [{"type": "text", "text": f"error: {e}"}],
                "isError": True,
            }

        if name == "add":
            text = str(a + b)
            is_error = False
        elif name == "subtract":
            text = str(a - b)
            is_error = False
        elif name == "multiply":
            text = str(a * b)
            is_error = False
        elif name == "divide":
            if b == 0:
                text = "error: division by zero"
                is_error = True
            else:
                text = str(a / b)
                is_error = False
        else:
            text = f"unknown tool: {name}"
            is_error = True

        return {
            "content": [{"type": "text", "text": text}],
            "isError": is_error,
        }

    raise ValueError(f"Method not found: {method}")


class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/" and self.path != "/mcp":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            return
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") or {}

        if req_id is None and method:
            self._send_json({})
            return

        try:
            result = handle_request(method, req_id, params)
            self._send_json({"jsonrpc": "2.0", "id": req_id, "result": result})
        except ValueError as e:
            self._send_json({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": str(e)}})

    def _send_json(self, obj: dict[str, Any]) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[MCP] {args[0]}")


def main() -> None:
    host = "127.0.0.1"
    port = 8765
    server = HTTPServer((host, port), MCPHandler)
    print(f"MCP server listening on http://{host}:{port}/")
    print("Start the Agent/CLI in another terminal; config should use url: http://127.0.0.1:8765/")
    server.serve_forever()


if __name__ == "__main__":
    main()
