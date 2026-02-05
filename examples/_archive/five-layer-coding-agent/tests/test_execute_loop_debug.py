"""Debug Execute Loop - why model doesn't return tool_calls."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from dare_framework.agent import FiveLayerAgent
from dare_framework.context import Message
from dare_framework.model import ModelInput
from dare_framework.plan.types import Task
from dare_framework.tool._internal.native_tool_provider import NativeToolProvider
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool
from dare_framework.tool.tool_manager import ToolManager


async def test_execute_loop_debug():
    """Debug Execute Loop to see why model doesn't call tools."""
    load_dotenv()

    workspace = Path(__file__).parent / "workspace"

    # Setup tools
    tools_list = [ReadFileTool(), SearchCodeTool(), WriteFileTool()]
    tool_provider = NativeToolProvider(tools=tools_list)
    tool_gateway = ToolManager()
    tool_gateway.register_provider(tool_provider)

    print("=" * 70)
    print("Testing Execute Loop - Model Tool Calling")
    print("=" * 70)

    # Create model adapter
    from dare_framework.model import OpenRouterModelAdapter
    model = OpenRouterModelAdapter()

    # Create agent with tools
    from planners.llm_planner import LLMPlanner
    planner = LLMPlanner(model, workspace, verbose=True)

    from validators import SimpleValidator
    validator = SimpleValidator()

    agent = FiveLayerAgent(
        name="test-agent",
        model=model,
        tools=tool_provider,
        tool_gateway=tool_gateway,
        planner=planner,
        validator=validator,
    )

    # Add user message asking to write snake game
    task_description = "写一个可以玩的贪吃蛇游戏，保存为 snake_game.py"
    agent._context.stm_add(Message(role="user", content=task_description))

    # Assemble context (same as Execute Loop does)
    assembled = agent._context.assemble()

    print(f"\n📋 Task: {task_description}")
    print(f"\n🔍 Assembled Context:")
    print(f"  Messages: {len(assembled.messages)} messages")
    print(f"  Tools: {len(assembled.tools)} tools")

    # Show messages
    print(f"\n📝 Messages being sent to model:")
    for i, msg in enumerate(assembled.messages, 1):
        content_preview = msg.content[:100] if msg.content else ""
        print(f"  {i}. [{msg.role}] {content_preview}...")

    # Show tools
    print(f"\n🔧 Tools being sent to model:")
    for i, tool in enumerate(assembled.tools, 1):
        func = tool.get('function', {})
        print(f"  {i}. {func.get('name', 'N/A')}: {func.get('description', 'N/A')[:60]}...")

    # Create model input (same as Execute Loop does)
    model_input = ModelInput(
        messages=assembled.messages,
        tools=assembled.tools,
        metadata=assembled.metadata,
    )

    print(f"\n⚙️ ModelInput created:")
    print(f"  Messages: {len(model_input.messages)}")
    print(f"  Tools: {len(model_input.tools)}")

    # Call model (same as Execute Loop does)
    print(f"\n🤖 Calling model.generate()...")
    print(f"   Model: {model.model_name}")

    response = await model.generate(model_input)

    print(f"\n📊 Model Response:")
    print(f"  Content length: {len(response.content) if response.content else 0} chars")
    print(f"  Tool calls: {len(response.tool_calls)} calls")

    if response.content:
        print(f"\n💬 Content (first 300 chars):")
        print(f"  {response.content[:300]}")

    if response.tool_calls:
        print(f"\n✅ SUCCESS: Model returned tool calls!")
        for i, tc in enumerate(response.tool_calls, 1):
            print(f"\n  Tool Call {i}:")
            print(f"    Name: {tc.get('name')}")
            print(f"    Arguments: {tc.get('arguments')}")
    else:
        print(f"\n❌ FAIL: Model did NOT return tool calls")
        print(f"   This is why Execute Loop exits immediately with success=True")
        print(f"   and doesn't create any files.")

        print(f"\n🔍 Possible reasons:")
        print(f"   1. Model is answering in Chinese (text response instead of tool call)")
        print(f"   2. Model doesn't understand it should use write_file tool")
        print(f"   3. Model thinks it's just explaining what to do")
        print(f"   4. System message or prompt doesn't instruct to use tools")

        print(f"\n💡 Solution:")
        print(f"   - Add system message instructing model to use tools")
        print(f"   - Check if STM contains system prompt")
        print(f"   - Verify model capabilities (some models ignore tools)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_execute_loop_debug())
