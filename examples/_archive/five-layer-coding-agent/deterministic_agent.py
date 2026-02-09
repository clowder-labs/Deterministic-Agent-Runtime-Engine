"""Deterministic agent for testing (no real model calls)."""
import asyncio
from pathlib import Path

from dare_framework.agent import FiveLayerAgent
from dare_framework.plan.types import ProposedPlan, ProposedStep, Task
from dare_framework.tool._internal.native_tool_provider import NativeToolProvider
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool
from dare_framework.tool.tool_manager import ToolManager

from planners import DeterministicPlanner
from validators import SimpleValidator


async def main():
    """Run deterministic agent example."""
    # Setup workspace
    workspace = Path(__file__).parent / "workspace"
    print(f"Workspace: {workspace}")

    # Create tools
    tools_list = [
        ReadFileTool(),
        SearchCodeTool(),
        WriteFileTool(),
    ]

    # Wrap in tool provider
    tool_provider = NativeToolProvider(tools=tools_list)

    # Create tool gateway and register provider
    tool_gateway = ToolManager()
    tool_gateway.register_provider(tool_provider)

    # Create a predefined plan
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

    # Create agent (mock model since we won't actually call it in deterministic mode)
    from unittest.mock import AsyncMock
    mock_model = AsyncMock()

    agent = FiveLayerAgent(
        name="deterministic-coding-agent",
        model=mock_model,
        tools=tool_provider,
        tool_gateway=tool_gateway,
        planner=planner,
        validator=validator,
    )

    # Run task
    task = Task(
        description="Read sample.py and find TODO comments",
        task_id="test-task-1",
    )

    print("\n=== Running Deterministic Agent ===")
    print(f"Task: {task.description}")
    print(f"Plan: {plan.plan_description}")
    print(f"Steps: {len(plan.steps)}")
    print()

    try:
        result = await agent.run(task)

        print("\n=== Result ===")
        print(f"Success: {result.success}")
        print(f"Output: {result.output}")
        if result.errors:
            print(f"Errors: {result.errors}")
    except Exception as e:
        print(f"\n=== Error ===")
        print(f"Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
