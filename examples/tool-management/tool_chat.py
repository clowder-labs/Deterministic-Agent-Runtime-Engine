"""Tool management chat example with a real model.

This mirrors the base_tool tool chat flow while keeping tool-management focus.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path for local development
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.context import Budget, Context, Message
from dare_framework.memory import InMemorySTM
from dare_framework.model import OpenAIModelAdapter, Prompt
from dare_framework.plan import Envelope
from dare_framework.tool import (
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

MODEL = os.getenv("CHAT_MODEL", "qwen-plus")
API_KEY = os.getenv("CHAT_API_KEY", "")
ENDPOINT = os.getenv("CHAT_ENDPOINT", "https://dashscope.aliyuncs.com/compatible-mode/v1")
HTTP_CLIENT_OPTIONS = {"trust_env": False, "proxy": None}
LOG_LEVEL = os.getenv("CHAT_LOG_LEVEL", "INFO").upper()
WORKSPACE_ROOT = os.getenv("TOOL_WORKSPACE_ROOT", ".")
MAX_TOOL_ROUNDS = int(os.getenv("TOOL_MAX_ROUNDS", "3"))

logger = logging.getLogger("tool-management-chat")


def _preview(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"


def _serialize_messages(messages: list[Message]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for msg in messages:
        serialized.append(
            {
                "role": msg.role,
                "content": msg.content,
                "name": msg.name,
                "metadata": dict(msg.metadata),
            }
        )
    return serialized


def _log_llm_request(prompt: Prompt) -> None:
    request_body = {
        "messages": _serialize_messages(prompt.messages),
        "tools": prompt.tools,
        "metadata": prompt.metadata,
    }
    logger.info("llm request body", extra={"request_body": request_body})
    print(json.dumps({"llm_request": request_body}, indent=2, sort_keys=True, ensure_ascii=False))


def _log_llm_response(response) -> None:
    response_body = {
        "content": response.content,
        "tool_calls": response.tool_calls,
        "usage": response.usage,
        "metadata": response.metadata,
    }
    logger.info("llm response body", extra={"response_body": response_body})
    print(json.dumps({"llm_response": response_body}, indent=2, sort_keys=True, ensure_ascii=False))


def _log_messages(messages: list[Message], *, label: str) -> None:
    logger.info(label, extra={"message_count": len(messages)})
    for idx, msg in enumerate(messages, start=1):
        logger.debug(
            "message",
            extra={
                "index": idx,
                "role": msg.role,
                "name": msg.name,
                "content": _preview(msg.content),
                "metadata_keys": list(msg.metadata.keys()),
            },
        )


def _log_tool_defs(tool_defs: list[dict[str, Any]]) -> None:
    tool_names = []
    for tool in tool_defs:
        function = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(function, dict):
            tool_names.append(function.get("name"))
    logger.info("tool defs loaded", extra={"tool_names": tool_names})


async def _execute_tool_calls(
    response,
    *,
    gateway: DefaultToolGateway,
    context: Context,
) -> bool:
    tool_calls = response.tool_calls
    if not tool_calls:
        return False

    context.stm_add(
        Message(
            role="assistant",
            content=response.content or "",
            metadata={"tool_calls": tool_calls},
        )
    )

    for idx, call in enumerate(tool_calls, start=1):
        tool_name = call.get("name")
        if not tool_name:
            logger.warning("tool call missing name", extra={"call": call})
            continue
        arguments = call.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {"raw": arguments}
        call_id = call.get("id") or f"tool_call_{idx}"
        capability_id = f"tool:{tool_name}"

        logger.info(
            "invoking tool",
            extra={
                "capability_id": capability_id,
                "call_id": call_id,
                "arguments": arguments,
            },
        )
        try:
            result = await gateway.invoke(
                capability_id,
                arguments,
                envelope=Envelope(allowed_capability_ids=[capability_id]),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("tool invocation failed")
            result_payload = {"success": False, "error": str(exc)}
        else:
            result_payload = {
                "success": result.success,
                "output": result.output,
                "error": result.error,
            }
            logger.info(
                "tool invocation result",
                extra={
                    "capability_id": capability_id,
                    "call_id": call_id,
                    "success": result.success,
                    "error": result.error,
                },
            )

        context.stm_add(
            Message(
                role="tool",
                name=call_id,
                content=json.dumps(result_payload),
                metadata={"tool_name": tool_name},
            )
        )

    return True


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

    gateway = DefaultToolGateway()
    gateway.register_provider(NativeToolProvider(tools=tools, context_factory=run_context.build))

    tool_provider = GatewayToolProvider(gateway)
    await tool_provider.refresh()
    _log_tool_defs(tool_provider.list_tools())

    context = Context(
        id="tool-management-chat",
        short_term_memory=InMemorySTM(),
        budget=Budget(),
    )
    context._tool_provider = tool_provider

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

        context.stm_add(Message(role="user", content=prompt))
        assembled = context.assemble()
        _log_messages(assembled.messages, label="assembled prompt")
        logger.info("llm request", extra={"tools": len(assembled.tools)})
        prompt_payload = Prompt(messages=assembled.messages, tools=assembled.tools, metadata=assembled.metadata)
        _log_llm_request(prompt_payload)
        response = await model_adapter.generate(prompt_payload)
        logger.info(
            "llm response",
            extra={
                "content": _preview(response.content),
                "tool_call_count": len(response.tool_calls),
                "usage": response.usage,
            },
        )
        _log_llm_response(response)

        rounds = 0
        while response.tool_calls and rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            logger.info("tool calls detected", extra={"count": len(response.tool_calls), "round": rounds})
            await _execute_tool_calls(response, gateway=gateway, context=context)
            assembled = context.assemble()
            _log_messages(assembled.messages, label="assembled prompt (post-tool)")
            logger.info("llm request (post-tool)", extra={"tools": len(assembled.tools)})
            prompt_payload = Prompt(messages=assembled.messages, tools=assembled.tools, metadata=assembled.metadata)
            _log_llm_request(prompt_payload)
            response = await model_adapter.generate(prompt_payload)
            logger.info(
                "llm response (post-tool)",
                extra={
                    "content": _preview(response.content),
                    "tool_call_count": len(response.tool_calls),
                    "usage": response.usage,
                },
            )
            _log_llm_response(response)

        if response.tool_calls and rounds >= MAX_TOOL_ROUNDS:
            logger.warning("tool rounds exhausted", extra={"max_rounds": MAX_TOOL_ROUNDS})

        if response.content:
            context.stm_add(Message(role="assistant", content=response.content))
            print(response.content, flush=True)
        else:
            print("No output returned.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
