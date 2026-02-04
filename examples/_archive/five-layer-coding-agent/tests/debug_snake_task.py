"""Debug script to test snake game task."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from dare_framework.agent import FiveLayerAgent
from dare_framework.context import Message
from dare_framework.plan.types import Task
from dare_framework.tool._internal.native_tool_provider import NativeToolProvider
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool
from dare_framework.tool.default_tool_manager import ToolManager

from planners.llm_planner import LLMPlanner
from validators import SimpleValidator


async def test_snake_task():
    """Test snake game creation task."""
    load_dotenv()

    workspace = Path(__file__).parent / "workspace"

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found")
        return

    from dare_framework.model import OpenRouterModelAdapter
    model = OpenRouterModelAdapter()

    print(f"✓ Using model: {model.model_name}")
    print(f"✓ Workspace: {workspace}")
    print()

    # Setup tools
    tools_list = [ReadFileTool(), SearchCodeTool(), WriteFileTool()]
    tool_provider = NativeToolProvider(tools=tools_list)
    tool_gateway = ToolManager()
    tool_gateway.register_provider(tool_provider)

    # Create planner
    planner = LLMPlanner(model, workspace, verbose=True)
    validator = SimpleValidator()

    agent = FiveLayerAgent(
        name="debug-agent",
        model=model,
        tools=tool_provider,
        tool_gateway=tool_gateway,
        planner=planner,
        validator=validator,
    )

    # Test task
    task_desc = "写一个可以玩的贪吃蛇游戏"
    print(f"📋 Task: {task_desc}")
    print("="*60)

    # Step 1: Generate plan
    print("\n🎯 STEP 1: Generating Plan...")
    print("-"*60)

    agent._context.stm_add(Message(role="user", content=task_desc))
    plan = await planner.plan(agent._context)

    print(f"\n✓ Plan generated!")
    print(f"Description: {plan.plan_description}")
    print(f"Steps ({len(plan.steps)}):")
    for i, step in enumerate(plan.steps, 1):
        print(f"  {i}. {step.capability_id} - {step.description}")
        print(f"     Params: {step.params}")

    # Check if plan is correct
    print("\n🔍 DIAGNOSIS:")
    print("-"*60)

    has_tool_calls = any(
        step.capability_id in ["read_file", "write_file", "search_code"]
        for step in plan.steps
    )

    has_evidence = any(
        step.capability_id.endswith("_evidence")
        for step in plan.steps
    )

    if has_tool_calls:
        print("❌ PROBLEM: Plan contains TOOL CALLS (read_file, write_file, etc.)")
        print("   Expected: Evidence types (file_evidence, code_evidence, etc.)")
    elif has_evidence:
        print("✓ GOOD: Plan contains EVIDENCE TYPES")
    else:
        print("⚠️  WARNING: Plan has unknown capability_ids")

    # Step 2: Execute (commented out to avoid actual execution)
    print("\n🚀 STEP 2: Execute Loop")
    print("-"*60)
    print("(Skipping actual execution for debugging)")

    # Show what should happen:
    print("\nExpected behavior:")
    print("1. Execute Loop should call write_file tool")
    print("2. Create snake.py file in workspace")
    print("3. Fill evidence: [✓] file_evidence: Created snake.py")


if __name__ == "__main__":
    asyncio.run(test_snake_task())
