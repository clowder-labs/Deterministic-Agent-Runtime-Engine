"""Basic chat example using SimpleChatAgentBuilder.

This is the simplest way to create a chat agent with DARE framework.
No tools, no planning - just pure conversation.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import BaseAgent
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.transport import AgentChannel, StdioClientChannel


async def main() -> None:
    """Run a simple chat loop."""
    # Configuration from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)

    model = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.7")

    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))

    # Create model adapter
    model_adapter = OpenRouterModelAdapter(
        model=model,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
    )

    # Build agent using SimpleChatAgentBuilder
    client_channel = StdioClientChannel()
    channel = AgentChannel.build(client_channel)

    agent = (
        BaseAgent.simple_chat_agent_builder("basic-chat")
        .with_model(model_adapter)
        .with_agent_channel(channel)
        .build()
    )

    print(f"Chat agent ready (model: {model})")
    print("Type your message, or /quit to exit.\n")

    await agent.start()
    try:
        await client_channel.start()
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
