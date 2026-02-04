"""Test if context.assemble() returns tools correctly."""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from dare_framework.agent import FiveLayerAgent
from dare_framework.context import Message
from dare_framework.tool._internal.native_tool_provider import NativeToolProvider
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool
from dare_framework.tool.default_tool_manager import ToolManager


async def test_assembled_tools():
    """Test if assembled context includes tools."""
    load_dotenv()

    workspace = Path(__file__).parent / "workspace"

    # Setup tools
    tools_list = [ReadFileTool(), SearchCodeTool(), WriteFileTool()]
    tool_provider = NativeToolProvider(tools=tools_list)
    tool_gateway = ToolManager()
    tool_gateway.register_provider(tool_provider)

    print("=" * 70)
    print("Testing Context.assemble() Tools")
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
        tools=tool_provider,  # ← Pass tools
        tool_gateway=tool_gateway,
        planner=planner,
        validator=validator,
    )

    print("\n🔍 Checking agent setup...")
    print(f"Agent._context type: {type(agent._context)}")
    print(f"Agent._context._tool_provider: {agent._context._tool_provider}")
    print(f"Agent._tool_gateway: {agent._tool_gateway}")

    # Add a test message
    agent._context.stm_add(Message(role="user", content="Test message"))

    # Assemble context
    print("\n🔍 Calling context.assemble()...")
    assembled = agent._context.assemble()

    print(f"\nAssembled context:")
    print(f"  Messages: {len(assembled.messages)} messages")
    print(f"  Tools: {len(assembled.tools)} tools")
    print(f"  Metadata: {assembled.metadata}")

    if assembled.tools:
        print(f"\n✓ Tools found in assembled context:")
        for i, tool in enumerate(assembled.tools, 1):
            print(f"  {i}. {tool.get('type', 'unknown')} - {tool.get('function', {}).get('name', 'N/A')}")
    else:
        print(f"\n❌ NO TOOLS in assembled context!")
        print(f"   This explains why Execute Loop doesn't call tools.")

    # Test listing_tools directly
    print(f"\n🔍 Calling context.listing_tools() directly...")
    tools = agent._context.listing_tools()
    print(f"  Result: {len(tools)} tools")
    if tools:
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_assembled_tools())
