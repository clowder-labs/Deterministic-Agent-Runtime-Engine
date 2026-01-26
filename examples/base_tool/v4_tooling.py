"""V4 tooling example using dare_framework3_4.

Demonstrates the v4.0 tool runtime with:
- Built-in file tools
- Trusted tool listings derived from the gateway registry
- Direct tool invocation via the gateway boundary
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path for local development
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework3_4.plan import Envelope
from dare_framework3_4.tool import (
    DefaultToolGateway,
    EditLineTool,
    GatewayToolProvider,
    NativeToolProvider,
    NoOpTool,
    ReadFileTool,
    RunCommandTool,
    RunContextState,
    SearchCodeTool,
    WriteFileTool,
)

# Configuration
WORKSPACE_ROOT = os.getenv("TOOL_WORKSPACE_ROOT", ".")
READ_PATH = os.getenv("TOOL_READ_PATH", "examples/base_tool/README.md")
LOG_LEVEL = os.getenv("TOOL_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("v4-tooling")


async def run_read_file(workspace_root: str, read_path: str):
    """Build the tool runtime and execute a read_file tool call."""
    run_context = RunContextState(
        config={
            "workspace_roots": [workspace_root],
            "tools": {
                "read_file": {"max_bytes": 1_000_000},
                "write_file": {"max_bytes": 1_000_000},
                "edit_line": {"max_bytes": 1_000_000},
                "search_code": {
                    "max_results": 50,
                    "max_file_bytes": 1_000_000,
                    "ignore_dirs": [".git", "node_modules", "__pycache__", ".venv", "venv"],
                },
            },
        }
    )

    tools = [
        ReadFileTool(),
        SearchCodeTool(),
        WriteFileTool(),
        EditLineTool(),
        RunCommandTool(),
        NoOpTool(),
    ]

    gateway = DefaultToolGateway()
    gateway.register_provider(NativeToolProvider(tools=tools, context_factory=run_context.build))

    tool_provider = GatewayToolProvider(gateway)
    await tool_provider.refresh()

    tool_defs = tool_provider.list_tools()
    result = await gateway.invoke(
        "tool:read_file",
        {"path": read_path},
        envelope=Envelope(),
    )
    return tool_defs, result


async def main() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info(
        "boot v4 tooling example",
        extra={
            "workspace_root": WORKSPACE_ROOT,
            "read_path": READ_PATH,
        },
    )

    tool_defs, result = await run_read_file(WORKSPACE_ROOT, READ_PATH)
    tool_names = [tool["function"]["name"] for tool in tool_defs]
    logger.info("tool defs ready", extra={"tool_names": tool_names})
    print(f"Tool defs: {tool_names}")

    logger.info("read_file completed", extra={"success": result.success})
    print(f"Read success: {result.success}")
    print(f"Read path: {result.output.get('path')}")


if __name__ == "__main__":
    asyncio.run(main())
