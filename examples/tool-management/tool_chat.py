"""Tool management chat example with a real model (builder-based).

This mirrors the base_tool tool chat flow while keeping tool-management focus.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path for local development
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.builder import Builder
from dare_framework.model import OpenAIModelAdapter
from dare_framework.tool import (
    EditLineTool,
    NoOpTool,
    ReadFileTool,
    RunCommandTool,
    RunContextState,
    SearchCodeTool,
    ToolManager,
    WriteFileTool,
)

MODEL = os.getenv("CHAT_MODEL", "qwen-plus")
API_KEY = os.getenv("CHAT_API_KEY", "")
ENDPOINT = os.getenv("CHAT_ENDPOINT", "https://dashscope.aliyuncs.com/compatible-mode/v1")
HTTP_CLIENT_OPTIONS = {"trust_env": False, "proxy": None}
LOG_LEVEL = os.getenv("CHAT_LOG_LEVEL", "INFO").upper()
WORKSPACE_ROOT = os.getenv("TOOL_WORKSPACE_ROOT", ".")

logger = logging.getLogger("tool-management-chat")


def _preview(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"


def _log_tool_defs(tool_defs: list[dict[str, object]]) -> None:
    tool_names = []
    for tool in tool_defs:
        function = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(function, dict):
            tool_names.append(function.get("name"))
    logger.info("tool defs loaded", extra={"tool_names": tool_names})


def _format_output(output: object | None) -> str:
    if output is None:
        return ""
    if isinstance(output, dict):
        content = output.get("content")
        if content:
            return str(content)
        try:
            return json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False)
        except TypeError:
            return str(output)
    return str(output)


async def main() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info(
        "boot tool-management chat",
        extra={
            "model": MODEL,
            "endpoint": ENDPOINT,
            "api_key_set": bool(API_KEY),
            "workspace_root": WORKSPACE_ROOT,
        },
    )

    model_adapter = OpenAIModelAdapter(
        model=MODEL,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        http_client_options=HTTP_CLIENT_OPTIONS,
    )

    run_context = RunContextState(
        config={
            "workspace_roots": [WORKSPACE_ROOT],
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

    gateway = ToolManager(context_factory=run_context.build)

    agent = (
        Builder.five_layer_agent_builder("tool-management-chat")
        .with_model(model_adapter)
        .with_tool_gateway(gateway)
        .add_tools(*tools)
        .build()
    )
    _log_tool_defs(agent.context.listing_tools())

    print("Tool Management Chat - Type your message (or /quit to exit):", flush=True)
    while True:
        try:
            raw = input("You: ")
        except EOFError:
            break
        prompt = raw.strip()
        if not prompt:
            continue
        if prompt == "/quit":
            break

        logger.info("running prompt", extra={"prompt": _preview(prompt)})
        try:
            result = await agent.run(prompt)
        except Exception as exc:  # noqa: BLE001
            logger.exception("agent run failed")
            print(f"[error] model call failed: {exc}", file=sys.stderr, flush=True)
            continue

        content = _format_output(result.output)
        if not content:
            if result.errors:
                print(f"[error] {', '.join(result.errors)}", file=sys.stderr, flush=True)
            else:
                print("No output returned.", flush=True)
            continue

        print(content, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
