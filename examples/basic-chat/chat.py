from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.builder import AgentBuilder
from dare_framework.components.model_adapters.openai import OpenAIModelAdapter
from dare_framework.components.tools.run_command import RunCommandTool

MODEL = "qwen-7b"
API_KEY = os.getenv("api_sk")
ENDPOINT = "http://127.0.0.1:8000/v1"
# httpx 0.28 (used by openai client) does not expose allow_env_proxies; set trust_env=False to bypass proxies.
HTTP_CLIENT_OPTIONS = {"trust_env": False, "proxy": None}
LOG_LEVEL = os.getenv("CHAT_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("basic-chat")


def _preview(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"


async def main() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info(
        "boot basic chat agent (v2 kernel)",
        extra={
            "model": MODEL,
            "endpoint": ENDPOINT,
            "api_key_set": bool(API_KEY),
            "trust_env": HTTP_CLIENT_OPTIONS.get("trust_env", True),
        },
    )

    agent = (
        AgentBuilder("basic-chat")
        .with_kernel_defaults()
        .with_model(
            OpenAIModelAdapter(
                model=MODEL,
                api_key=API_KEY,
                endpoint=ENDPOINT,
                http_client_options=HTTP_CLIENT_OPTIONS,
            )
        )
        .with_tools(RunCommandTool())
        .build()
    )

    while True:
        try:
            raw = input()
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
            logger.exception("agent run failed", extra={"model": MODEL, "endpoint": ENDPOINT})
            print(f"[error] model call failed: {exc}", file=sys.stderr, flush=True)
            continue

        if not result.success:
            logger.warning("agent returned failure", extra={"errors": result.errors})
            print(f"[error] run failed: {result.errors}", file=sys.stderr, flush=True)
            continue

        content = ""
        if isinstance(result.output, list) and result.output:
            last = result.output[-1]
            content = getattr(last, "output", {}).get("content", "")
        if not content:
            logger.warning("no content returned from agent")
            print("No output returned.", flush=True)
            continue

        logger.info("assistant reply", extra={"content": _preview(content)})
        print(content, flush=True)


if __name__ == "__main__":
    asyncio.run(main())

