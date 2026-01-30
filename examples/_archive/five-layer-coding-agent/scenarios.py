"""Example scenarios demonstrating the five-layer coding agent.

Run different scenarios to see the agent in action:
    python scenarios.py read-and-search
    python scenarios.py find-todos
    python scenarios.py analyze-code
"""
import asyncio
import sys
from pathlib import Path

from dare_framework.agent import FiveLayerAgent
from dare_framework.plan.types import ProposedPlan, ProposedStep, Task
from dare_framework.tool import (
    ReadFileTool,
    WriteFileTool,
    SearchCodeTool,
    NativeToolProvider,
    DefaultToolGateway,
)

from planners import DeterministicPlanner
from validators import SimpleValidator


def create_agent(plan: ProposedPlan) -> FiveLayerAgent:
    """Create an agent with the given plan."""
    from unittest.mock import AsyncMock

    # Setup workspace
    workspace = Path(__file__).parent / "workspace"

    # Create tools
    tools_list = [
        ReadFileTool(),
        SearchCodeTool(),
        WriteFileTool(),
    ]

    tool_provider = NativeToolProvider(tools=tools_list)
    tool_gateway = DefaultToolGateway()
    tool_gateway.register_provider(tool_provider)

    # Create planner and validator
    planner = DeterministicPlanner(plan)
    validator = SimpleValidator()

    # Mock model for deterministic execution
    mock_model = AsyncMock()

    return FiveLayerAgent(
        name="scenario-agent",
        model=mock_model,
        tools=tool_provider,
        tool_gateway=tool_gateway,
        planner=planner,
        validator=validator,
    )


async def scenario_read_and_search():
    """Scenario 1: Read a file and search for patterns."""
    print("\n" + "=" * 70)
    print("📖 Scenario 1: Read and Search")
    print("=" * 70)
    print("Task: Read sample.py and find TODO comments")
    print()

    workspace = Path(__file__).parent / "workspace"

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
                description="Search for TODO comments in all Python files",
            ),
        ],
    )

    agent = create_agent(plan)
    task = Task(description="Read and search for TODOs", task_id="scenario-1")

    result = await agent.run(task)
    print(f"\n✓ Result: Success={result.success}")
    if result.errors:
        print(f"  Errors: {result.errors}")


async def scenario_find_todos():
    """Scenario 2: Find all TODO comments."""
    print("\n" + "=" * 70)
    print("🔍 Scenario 2: Find All TODOs")
    print("=" * 70)
    print("Task: Search for all TODO comments in the workspace")
    print()

    plan = ProposedPlan(
        plan_description="Find all TODO comments",
        steps=[
            ProposedStep(
                step_id="step1",
                capability_id="search_code",
                params={"pattern": "TODO", "file_pattern": "*.py"},
                description="Search for TODO in all Python files",
            ),
        ],
    )

    agent = create_agent(plan)
    task = Task(description="Find all TODOs", task_id="scenario-2")

    result = await agent.run(task)
    print(f"\n✓ Result: Success={result.success}")
    if result.errors:
        print(f"  Errors: {result.errors}")


async def scenario_analyze_code():
    """Scenario 3: Analyze code structure."""
    print("\n" + "=" * 70)
    print("🔬 Scenario 3: Analyze Code Structure")
    print("=" * 70)
    print("Task: Read sample files and search for function definitions")
    print()

    workspace = Path(__file__).parent / "workspace"

    plan = ProposedPlan(
        plan_description="Analyze code structure by finding function definitions",
        steps=[
            ProposedStep(
                step_id="step1",
                capability_id="read_file",
                params={"path": str(workspace / "sample.py")},
                description="Read the main sample file",
            ),
            ProposedStep(
                step_id="step2",
                capability_id="search_code",
                params={"pattern": r"^def\s+\w+", "file_pattern": "*.py"},
                description="Search for function definitions",
            ),
        ],
    )

    agent = create_agent(plan)
    task = Task(description="Analyze code structure", task_id="scenario-3")

    result = await agent.run(task)
    print(f"\n✓ Result: Success={result.success}")
    if result.errors:
        print(f"  Errors: {result.errors}")


async def main():
    """Run scenarios based on command line argument."""
    scenarios = {
        "read-and-search": scenario_read_and_search,
        "find-todos": scenario_find_todos,
        "analyze-code": scenario_analyze_code,
        "all": None,  # Run all scenarios
    }

    if len(sys.argv) < 2 or sys.argv[1] not in scenarios:
        print("Usage: python scenarios.py <scenario>")
        print("\nAvailable scenarios:")
        for name in scenarios:
            print(f"  - {name}")
        print("\nExample:")
        print("  python scenarios.py read-and-search")
        print("  python scenarios.py all")
        return

    scenario = sys.argv[1]

    if scenario == "all":
        # Run all scenarios
        await scenario_read_and_search()
        await scenario_find_todos()
        await scenario_analyze_code()
    else:
        # Run specific scenario
        await scenarios[scenario]()

    print("\n" + "=" * 70)
    print("✓ Scenario(s) completed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
