"""OpenRouter agent with real model calls."""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from dare_framework.agent import FiveLayerAgent
from dare_framework.context import Message
from dare_framework.plan.types import ProposedPlan, ProposedStep, Task
from dare_framework.tool._internal.native_tool_provider import NativeToolProvider
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool
from dare_framework.tool.default_tool_manager import ToolManager

from dare_framework.model import OpenRouterModelAdapter
from planners import DeterministicPlanner
from validators import SimpleValidator


async def main():
    """Run OpenRouter agent example with real model."""
    # Load environment variables from .env file
    load_dotenv()

    # Setup workspace
    workspace = Path(__file__).parent / "workspace"
    print(f"Workspace: {workspace}")
    print()

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not found in environment")
        print("\nPlease create a .env file:")
        print("  cp .env.example .env")
        print("  # Edit .env and add your OPENROUTER_API_KEY")
        return

    model_name = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder:free")
    print(f"✓ Using OpenRouter API")
    print(f"✓ Model: {model_name}")
    print()

    # Create tools
    tools_list = [
        ReadFileTool(),
        SearchCodeTool(),
        WriteFileTool(),
    ]

    # Wrap in tool provider and gateway
    tool_provider = NativeToolProvider(tools=tools_list)
    tool_gateway = ToolManager()
    tool_gateway.register_provider(tool_provider)

    # Create real model adapter
    try:
        model = OpenRouterModelAdapter()
    except Exception as e:
        print(f"❌ Error creating model adapter: {e}")
        print("\nMake sure you have installed: pip install openai python-dotenv")
        return

    # For this demo, we'll use a simple predefined plan
    # In a full implementation, a real planner would call the model to generate plans
    plan = ProposedPlan(
        plan_description="Read sample.py and search for TODO comments",
        steps=[
            ProposedStep(
                step_id="step1",
                capability_id="read_file",
                params={"path": str(workspace / "sample.py")},
                description="Read the sample.py file",
            ),
            ProposedStep(
                step_id="step2",
                capability_id="search_code",
                params={"pattern": "TODO", "file_pattern": "*.py"},
                description="Search for TODO comments",
            ),
        ],
    )

    # Create planner and validator
    planner = DeterministicPlanner(plan)
    validator = SimpleValidator()

    # Create agent with real model
    agent = FiveLayerAgent(
        name="openrouter-coding-agent",
        model=model,
        tools=tool_provider,
        tool_gateway=tool_gateway,
        planner=planner,
        validator=validator,
    )

    # Run task
    task = Task(
        description="Read sample.py and find all TODO comments",
        task_id="openrouter-task-1",
    )

    print("=" * 70)
    print("🚀 Running OpenRouter Agent")
    print("=" * 70)
    print(f"Task: {task.description}")
    print(f"Plan: {plan.plan_description}")
    print(f"Steps: {len(plan.steps)}")
    print()

    try:
        result = await agent.run(task)

        print("\n" + "=" * 70)
        print("📊 Result")
        print("=" * 70)
        print(f"Success: {'✓' if result.success else '✗'} {result.success}")
        print(f"Output: {result.output}")
        if result.errors:
            print(f"Errors: {result.errors}")
    except Exception as e:
        print(f"\n❌ Error running agent: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
