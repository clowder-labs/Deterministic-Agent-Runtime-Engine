"""End-to-end test for snake game scenario with enhanced agent."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from dare_framework.context import Message
from dare_framework.plan.types import Task
from dare_framework.tool._internal.native_tool_provider import NativeToolProvider
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool
from dare_framework.tool.default_tool_manager import ToolManager

from enhanced_agent import EnhancedFiveLayerAgent
from cli_display import CLIDisplay
from evidence_tracker import extract_evidence_from_agent


async def test_snake_game_scenario():
    """Test complete snake game scenario: plan → execute → verify evidence."""
    load_dotenv()

    workspace = Path(__file__).parent / "workspace"

    print("=" * 70)
    print("🐍 End-to-End Test: Snake Game Scenario")
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

    # Create model adapter
    from dare_framework.model import OpenRouterModelAdapter
    model = OpenRouterModelAdapter()
    print(f"✓ Model: {model.model_name}\n")

    # Create planner
    from planners.llm_planner import LLMPlanner
    planner = LLMPlanner(model, workspace, verbose=True)

    # Create validator
    from validators import SimpleValidator
    validator = SimpleValidator()

    # Create ENHANCED agent with system message
    agent = EnhancedFiveLayerAgent(
        name="snake-game-agent",
        model=model,
        tools=tool_provider,
        tool_gateway=tool_gateway,
        planner=planner,
        validator=validator,
    )

    print("✓ Agent created (Enhanced with system message for tool calling)\n")

    # Task description
    task_description = "写一个可以玩的贪吃蛇游戏，保存为 snake_game.py"

    print(f"📋 Task: {task_description}\n")

    # Step 1: Generate Plan
    print("=" * 70)
    print("STEP 1: Generate Plan")
    print("=" * 70)

    agent._context.stm_add(Message(role="user", content=task_description))

    try:
        plan = await planner.plan(agent._context)
        print(f"\n✓ Plan generated!")
        print(f"  Description: {plan.plan_description}")
        print(f"  Steps: {len(plan.steps)}")

        for i, step in enumerate(plan.steps, 1):
            print(f"\n  {i}. {step.description}")
            print(f"     Type: {step.capability_id}")
            if step.params:
                print(f"     Params: {step.params}")
    except Exception as e:
        print(f"❌ Failed to generate plan: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 2: Execute Plan
    print("\n" + "=" * 70)
    print("STEP 2: Execute Plan (ReAct Mode with System Message)")
    print("=" * 70)

    task = Task(
        description=task_description,
        task_id="snake-game-task-1"
    )

    try:
        print("\n🤖 Running agent with enhanced Execute Loop...")
        print("   (System message instructs model to use tools)\n")

        result = await agent.run(task)

        print(f"\n📊 Execution Result:")
        print(f"  Success: {result.success}")

        if result.output:
            print(f"  Output: {result.output}")

        if result.errors:
            print(f"  Errors: {result.errors}")

    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Extract Evidence
    print("\n" + "=" * 70)
    print("STEP 3: Extract Evidence")
    print("=" * 70)

    evidence = await extract_evidence_from_agent(agent, plan)

    display = CLIDisplay()
    display.show_plan(plan, evidence=evidence)

    # Step 4: Verify File Created
    print("\n" + "=" * 70)
    print("STEP 4: Verify File Created")
    print("=" * 70)

    snake_file = workspace / "snake_game.py"
    if snake_file.exists():
        print(f"✅ SUCCESS: snake_game.py created!")
        print(f"   Path: {snake_file}")
        print(f"   Size: {snake_file.stat().st_size} bytes")

        # Show first few lines
        with open(snake_file, 'r') as f:
            lines = f.readlines()[:10]
            print(f"\n   First 10 lines:")
            for i, line in enumerate(lines, 1):
                print(f"     {i}: {line.rstrip()}")
    else:
        print(f"❌ FAIL: snake_game.py NOT created")
        print(f"   Expected path: {snake_file}")

    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_snake_game_scenario())
