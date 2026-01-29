"""Test if system message is properly sent to model in Execute Loop."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from dare_framework.context import Message
from dare_framework.plan.types import Task
from dare_framework.tool import (
    ReadFileTool,
    WriteFileTool,
    SearchCodeTool,
    NativeToolProvider,
    DefaultToolGateway,
)

from enhanced_agent import EnhancedFiveLayerAgent


async def test_system_message():
    """Test if system message is being sent to model."""
    load_dotenv()

    workspace = Path(__file__).parent / "workspace"

    print("=" * 70)
    print("Testing System Message in Execute Loop")
    print("=" * 70)

    # Setup tools
    tools_list = [ReadFileTool(), SearchCodeTool(), WriteFileTool()]
    tool_provider = NativeToolProvider(tools=tools_list)
    tool_gateway = DefaultToolGateway()
    tool_gateway.register_provider(tool_provider)

    # Create model adapter
    from model_adapters import OpenRouterModelAdapter
    model = OpenRouterModelAdapter()

    # Create agent WITHOUT planner (ReAct mode)
    agent = EnhancedFiveLayerAgent(
        name="test-agent",
        model=model,
        tools=tool_provider,
        tool_gateway=tool_gateway,
        planner=None,  # ← No planner = ReAct mode
        validator=None,
    )

    print(f"✓ Agent mode: {agent.is_react_mode} (ReAct)")
    print(f"✓ Agent mode: {agent.is_full_five_layer_mode} (Full Five-Layer)\n")

    # Add user message
    task_description = "写一个文件 test.txt，内容是 hello world"
    agent._context.stm_add(Message(role="user", content=task_description))

    # Manually call _run_execute_loop (simulating what agent.run() does)
    print(f"📋 Task: {task_description}\n")
    print(f"🔍 Calling _run_execute_loop manually...\n")

    # Assemble to see what messages are being sent
    assembled = agent._context.assemble()

    print(f"📝 Messages in assembled context (BEFORE enhancement):")
    for i, msg in enumerate(assembled.messages, 1):
        content_preview = msg.content[:100] if msg.content else ""
        print(f"  {i}. [{msg.role}] {content_preview}...")

    # Now call _run_execute_loop which should add system message
    print(f"\n🤖 Calling enhanced _run_execute_loop...\n")

    result = await agent._run_execute_loop(None)

    print(f"\n📊 Result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Outputs: {result.get('outputs')}")
    print(f"  Errors: {result.get('errors')}")

    # Check if file was created
    test_file = workspace / "test.txt"
    if test_file.exists():
        print(f"\n✅ SUCCESS: test.txt created!")
        with open(test_file, 'r') as f:
            print(f"   Content: {f.read()}")
    else:
        print(f"\n❌ FAIL: test.txt NOT created")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_system_message())
