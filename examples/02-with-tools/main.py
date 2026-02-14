"""Agent with tools example using ReactAgentBuilder.

This example shows how to add tools to an agent for file operations.
The agent uses ReAct mode: reason → act → observe loop (ReactAgent executes tool_calls).

Built-in tools:
- ask_user is automatically registered for every agent. When the LLM needs
  user clarification, a decision, or approval, it calls ask_user with
  structured questions. By default a CLI handler (stdin/stdout) is used.
  To use a custom UI, call .with_user_input_handler(your_handler) on the builder.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import BaseAgent
from dare_framework.config import Config
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool
from dare_framework.tool._internal.tools.ask_user import IUserInputHandler
from dare_framework.transport import AgentChannel, StdioClientChannel


# ---------------------------------------------------------------------------
# (Optional) Custom user-input handler example
# Replace CLIUserInputHandler when building a web UI, Slack bot, etc.
# ---------------------------------------------------------------------------

class CustomUserInputHandler(IUserInputHandler):
    """Example custom handler — adapt for any UI."""

    async def handle(self, questions: list[dict[str, Any]]) -> dict[str, str]:
        answers: dict[str, str] = {}
        for q in questions:
            question_text = q.get("question", "")
            options = q.get("options", [])

            print(f"\n>>> {q.get('header', '')}: {question_text}")
            for i, opt in enumerate(options, 1):
                print(f"    [{i}] {opt['label']}: {opt.get('description', '')}")

            loop = asyncio.get_running_loop()
            raw = await loop.run_in_executor(
                None, lambda: input("  → ").strip()
            )

            try:
                idx = int(raw) - 1
                answers[question_text] = options[idx]["label"]
            except (ValueError, IndexError):
                answers[question_text] = raw

        return answers


async def main() -> None:
    """Run an agent with file tools."""
    # Configuration from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)

    model_name = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.7")
    workspace = Path(__file__).parent / "workspace"
    workspace.mkdir(exist_ok=True)

    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))

    # Create model adapter
    model_adapter = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
    )

    # Create tools
    read_tool = ReadFileTool()
    write_tool = WriteFileTool()
    search_tool = SearchCodeTool()

    agent_config = Config(
        workspace_dir=str(workspace),
        user_dir=str(Path.home()),
    )

    client_channel = StdioClientChannel()
    channel = AgentChannel.build(client_channel)

    # Build agent with tools (ReactAgent executes tool_calls in a ReAct loop)
    # Note: ask_user tool is built-in — no need to add it explicitly.
    # To use a custom handler, uncomment the line below:
    #   .with_user_input_handler(CustomUserInputHandler())
    agent = await (
        BaseAgent.react_agent_builder("tool-agent")
        .with_model(model_adapter)
        .with_config(agent_config)
        .add_tools(read_tool, write_tool, search_tool)
        .with_agent_channel(channel)
        .build()
    )

    print(f"Tool agent ready (model: {model_name})")
    print(f"Workspace: {workspace}")
    print("The agent can ask you questions when it needs your input.")
    print("Type your request, or /quit to exit.\n")

    await agent.start()
    try:
        await client_channel.start()
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
