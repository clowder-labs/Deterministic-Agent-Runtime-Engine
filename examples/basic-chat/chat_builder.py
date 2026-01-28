"""Chat example using Builder for composition."""

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

from dare_framework.builder import Builder
from dare_framework.model import OpenAIModelAdapter

# Configuration
MODEL = "qwen-7b"
API_KEY = os.getenv("api_sk")
ENDPOINT = "http://127.0.0.1:8000/v1"
# httpx 0.28 (used by openai client) does not expose allow_env_proxies; set trust_env=False to bypass proxies.
HTTP_CLIENT_OPTIONS = {"trust_env": False, "proxy": None}
LOG_LEVEL = os.getenv("CHAT_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("basic-chat-builder")


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
        "boot basic chat agent (dare_framework)",
        extra={
            "model": MODEL,
            "endpoint": ENDPOINT,
            "api_key_set": bool(API_KEY),
            "trust_env": HTTP_CLIENT_OPTIONS.get("trust_env", True),
        },
    )

    model_adapter = OpenAIModelAdapter(
        model=MODEL,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        http_client_options=HTTP_CLIENT_OPTIONS,
    )
    agent = Builder.simple_chat_agent_builder("basic-chat-builder").with_model(model_adapter).build()

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

        content = str(result.output or "")
        if not content:
            logger.warning("no content returned from agent")
            print("No output returned.", flush=True)
            continue

        logger.info("assistant reply", extra={"content": _preview(content)})
        print(content, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
