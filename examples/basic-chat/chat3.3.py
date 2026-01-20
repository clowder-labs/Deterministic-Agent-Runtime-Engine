"""Basic chat example using dare_framework3_3.

This demonstrates the v3.3 architecture with:
- kernel interfaces populated per domain
- impl/ renamed to internal/
- explicit scope tags on interfaces
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

# Clean imports from dare_framework3_3
from dare_framework3_3 import FiveLayerAgent

# Model adapter - direct import from internal
from dare_framework3_3.model import OpenAIModelAdapter

# Tools - direct import from internal
from dare_framework3_3.tool import RunCommandTool

# Configuration - fill in your values
MODEL = "qwen-plus"       # e.g., "qwen-plus"
API_KEY = "sk-27ba4fe0c64d45a3b5bc3f06312189ac"              # your API key
ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# httpx 0.28 (used by openai client) does not expose allow_env_proxies; set trust_env=False to bypass proxies.
HTTP_CLIENT_OPTIONS = {"trust_env": False, "proxy": None}
LOG_LEVEL = os.getenv("CHAT_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("basic-chat-v3_3")


def _preview(text: str, limit: int = 200) -> str:
    """Truncate text for logging preview."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"


async def main() -> None:
    """Main entry point for the basic chat agent."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info(
        "boot basic chat agent (dare_framework3_3)",
        extra={
            "model": MODEL,
            "endpoint": ENDPOINT,
            "api_key_set": bool(API_KEY),
            "trust_env": HTTP_CLIENT_OPTIONS.get("trust_env", True),
        },
    )

    # Build model adapter (direct import, no factory)
    model_adapter = OpenAIModelAdapter(
        model=MODEL,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        http_client_options=HTTP_CLIENT_OPTIONS,
    )

    # Create agent using dare_framework3_3's FiveLayerAgent
    agent = FiveLayerAgent(
        name="basic-chat-v3_3",
        model=model_adapter,
        tools=[RunCommandTool()],
    )

    # Interactive chat loop
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

        # Extract content from result
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
