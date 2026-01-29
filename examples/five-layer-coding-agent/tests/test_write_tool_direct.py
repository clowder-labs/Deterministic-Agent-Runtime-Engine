"""Test WriteFileTool directly to see if it works."""
import asyncio
from pathlib import Path
from dare_framework.tool import WriteFileTool, NativeToolProvider, DefaultToolGateway
from dare_framework.tool.types import Envelope


async def test_write_tool_direct():
    """Test WriteFileTool directly."""
    workspace = Path(__file__).parent / "workspace"
    workspace.mkdir(exist_ok=True)

    print("=" * 70)
    print("Testing WriteFileTool directly")
    print("=" * 70)
    print(f"Workspace: {workspace}\n")

    # Create tool
    write_tool = WriteFileTool()

    # Check if tool has workspace_roots or similar config
    print(f"WriteFileTool attributes: {dir(write_tool)}\n")

    # Create provider and gateway
    tool_provider = NativeToolProvider(tools=[write_tool])
    tool_gateway = DefaultToolGateway()
    tool_gateway.register_provider(tool_provider)

    # Try to invoke write_file
    print("Invoking write_file tool...")

    # Create envelope
    envelope = Envelope(
        allowed_capability_ids=None,  # Allow all
        workspace_roots=[str(workspace)],  # Set workspace root
    )

    try:
        result = await tool_gateway.invoke(
            "tool:write_file",
            {
                "path": str(workspace / "direct_test.txt"),
                "content": "Direct test content"
            },
            envelope=envelope
        )

        print(f"\n✓ Tool invocation succeeded!")
        print(f"  Result: {result}")

        # Check if file exists
        test_file = workspace / "direct_test.txt"
        if test_file.exists():
            print(f"\n✅ File created: {test_file}")
            with open(test_file, 'r') as f:
                print(f"   Content: {f.read()}")
        else:
            print(f"\n❌ File NOT created at {test_file}")

    except Exception as e:
        print(f"\n❌ Tool invocation failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_write_tool_direct())
