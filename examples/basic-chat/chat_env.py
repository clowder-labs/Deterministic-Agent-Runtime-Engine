"""Chat example configured via environment variables."""

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

from dare_framework.agent import SimpleChatAgent
from dare_framework.model import OpenAIModelAdapter

# Configuration
MODEL = os.getenv("CHAT_MODEL", "qwen-plus")  # e.g., "qwen-plus", "gpt-4o-mini"
API_KEY = os.getenv("CHAT_API_KEY", "")  # your API key
ENDPOINT = os.getenv("CHAT_ENDPOINT", "https://dashscope.aliyuncs.com/compatible-mode/v1")
# httpx 0.28 (used by openai client) does not expose allow_env_proxies; set trust_env=False to bypass proxies.
HTTP_CLIENT_OPTIONS = {"trust_env": False, "proxy": None}
LOG_LEVEL = os.getenv("CHAT_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("basic-chat-env")


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
        },
    )

    # Create model adapter
    model_adapter = OpenAIModelAdapter(
        model=MODEL,
        api_key=API_KEY,
        endpoint=ENDPOINT,
        http_client_options=HTTP_CLIENT_OPTIONS,
    )
    logger.info("using OpenAIModelAdapter")

    agent = SimpleChatAgent(
        name="basic-chat-env",
        model=model_adapter,
    )

    logger.info("agent created", extra={"agent_name": agent.name})

    # Interactive chat loop
    print("SimpleChatAgent - Type your message (or /quit to exit):", flush=True)
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

        content = str(result.output or "")
        if not content:
            logger.warning("no content returned from agent")
            print("No output returned.", flush=True)
            continue

        logger.info("assistant reply", extra={"content": _preview(content)})
        print(content, flush=True)

        # Show context state (optional, for debugging)
        if LOG_LEVEL == "DEBUG":
            messages = agent.context.stm_get()
            logger.debug(
                "context state",
                extra={
                    "message_count": len(messages),
                    "budget_used_tokens": agent.context.budget.used_tokens,
                },
            )


if __name__ == "__main__":
    asyncio.run(main())
