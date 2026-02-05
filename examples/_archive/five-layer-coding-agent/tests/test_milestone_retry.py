"""Test Milestone Loop retry mechanism.

This test verifies that when Execute Loop fails (model doesn't call tools),
the Milestone Loop triggers retry with Remediate → Plan → Execute.
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from dare_framework.plan.types import Task
from dare_framework.tool._internal.native_tool_provider import NativeToolProvider
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool
from dare_framework.tool.tool_manager import ToolManager

from enhanced_agent import EnhancedFiveLayerAgent


async def test_milestone_retry():
    """Test that Milestone Loop retries when verification fails."""
    load_dotenv()

    workspace = Path(__file__).parent / "workspace"
    workspace.mkdir(exist_ok=True)

    print("=" * 70)
    print("🔄 Testing Milestone Loop Retry Mechanism")
    print("=" * 70)

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found")
        return

    # Setup tools
    tools_list = [ReadFileTool(), SearchCodeTool(), WriteFileTool()]
    tool_provider = NativeToolProvider(tools=tools_list)
    tool_gateway = ToolManager()
    tool_gateway.register_provider(tool_provider)

    # Create model
    from dare_framework.model import OpenRouterModelAdapter
    model = OpenRouterModelAdapter()
    print(f"✓ Model: {model.model_name}")

    # Create planner
    from planners.llm_planner import LLMPlanner
    planner = LLMPlanner(model, workspace, verbose=True)

    # Create validator (fixed version - no longer always returns True)
    from validators import SimpleValidator
    validator = SimpleValidator()

    # Create remediator (optional - leave None for MVP)
    remediator = None  # MVP: No remediator

    # Create agent with retry enabled
    agent = EnhancedFiveLayerAgent(
        name="retry-test-agent",
        model=model,
        tools=tool_provider,
        tool_gateway=tool_gateway,
        planner=planner,
        validator=validator,
        remediator=remediator,
        max_milestone_attempts=3,  # ← Allow 3 retries
    )

    print(f"✓ Agent created with max_milestone_attempts=3")
    print()

    # Task
    task = Task(
        description="写一个可以玩的贪吃蛇游戏，保存为 snake_game.py",
        task_id="retry-test-1"
    )

    print("📋 Task: 写一个可以玩的贪吃蛇游戏，保存为 snake_game.py")
    print()
    print("🔍 Expected behavior:")
    print("  1. Attempt 1: Model returns text → Verify FAIL → Trigger retry")
    print("  2. Attempt 2: Retry with reflection → May succeed or fail")
    print("  3. Attempt 3: Final retry if needed")
    print()
    print("=" * 70)
    print("🚀 Running agent.run(task)...")
    print("=" * 70)
    print()

    try:
        result = await agent.run(task)

        print("\n" + "=" * 70)
        print("📊 Final Result")
        print("=" * 70)
        print(f"Success: {result.success}")

        if result.success:
            print(f"✅ Task completed successfully!")

            # Check if file was created
            snake_file = workspace / "snake_game.py"
            if snake_file.exists():
                print(f"\n✅ File created: {snake_file}")
                print(f"   Size: {snake_file.stat().st_size} bytes")

                # Show first few lines
                with open(snake_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]
                    print(f"\n   First 10 lines:")
                    for i, line in enumerate(lines, 1):
                        print(f"     {i}: {line.rstrip()}")
            else:
                print(f"\n⚠️ Warning: Task succeeded but file not found at {snake_file}")
                print(f"   This might indicate an issue with workspace configuration")
        else:
            print(f"❌ Task failed after {agent._max_milestone_attempts} attempts")

        if result.output:
            print(f"\nOutput: {result.output}")

        if result.errors:
            print(f"\nErrors:")
            for error in result.errors:
                print(f"  - {error}")

    except Exception as e:
        print(f"\n❌ Exception during execution: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_milestone_retry())
