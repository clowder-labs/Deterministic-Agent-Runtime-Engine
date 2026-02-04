"""Test what capability_id tools use."""
from dare_framework.tool._internal.native_tool_provider import NativeToolProvider
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool


def test_capability_ids():
    """Check what capability_id each tool uses."""
    print("=" * 70)
    print("Testing Tool Capability IDs")
    print("=" * 70)

    tools_list = [ReadFileTool(), SearchCodeTool(), WriteFileTool()]
    tool_provider = NativeToolProvider(tools=tools_list)

    # List tools
    tool_list = tool_provider.list_tools()

    print(f"\nTools provided by NativeToolProvider ({len(tool_list)} tools):\n")

    for i, tool_def in enumerate(tool_list, 1):
        func = tool_def.get('function', {})
        capability_id = tool_def.get('capability_id', 'N/A')
        function_name = func.get('name', 'N/A')

        print(f"{i}. Function name (sent to model): {function_name}")
        print(f"   Capability ID (used by gateway): {capability_id}")
        print(f"   Type: {tool_def.get('type', 'N/A')}")
        print()

    print("=" * 70)
    print("\nISSUE: Model returns function names (e.g., 'write_file')")
    print("       But gateway expects capability IDs (e.g., 'tool:write_file')")
    print("\nSOLUTION: Map function names to capability IDs in Execute Loop")
    print("=" * 70)


if __name__ == "__main__":
    test_capability_ids()
