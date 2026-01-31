"""Agent with tools example using ReactAgentBuilder.

This example shows how to add tools to an agent for file operations.
The agent uses ReAct mode: reason → act → observe loop (ReactAgent executes tool_calls).
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
from dare_framework.tool import ReadFileTool, RunContext, WriteFileTool, SearchCodeTool


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

    # Run context for tools: 可执行空间 = 本示例 workspace + D:\Agent\tests
    def run_context_factory():
        return RunContext(
            config={
                "workspace_roots": [str(workspace)],
            },
            deps=None,
            metadata={"agent": "tool-agent"},
        )

    # Build agent with tools (ReactAgent executes tool_calls in a ReAct loop)
    agent = (
        BaseAgent.react_agent_builder("tool-agent")
        .with_model(model_adapter)
        .with_run_context_factory(run_context_factory)
        .add_tools(read_tool, write_tool, search_tool)
        .build()
    )

    print(f"Tool agent ready (model: {model_name})")
    print(f"Workspace: {workspace}")
    print("Type your request, or /quit to exit.\n")

    while True:
        try:
            prompt = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not prompt:
            continue
        if prompt == "/quit":
            break

        # Include workspace context
        full_prompt = f"Workspace: {workspace}\n\n{prompt}"
        result = await agent.run(full_prompt)
        print(f"\nAssistant: {result.output}\n")


if __name__ == "__main__":
    asyncio.run(main())
