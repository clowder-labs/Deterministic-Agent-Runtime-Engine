"""Test if model uses tools (function calling)."""
import asyncio
import os
from dotenv import load_dotenv

from dare_framework.model import Prompt
from dare_framework.context import Message


async def test_tool_use():
    """Test if OpenRouter model can use tools."""
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found")
        return

    from model_adapters import OpenRouterModelAdapter
    model = OpenRouterModelAdapter()

    print(f"✓ Using model: {model.model_name}")
    print(f"="*70)

    # Create a prompt with tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path"
                        },
                        "content": {
                            "type": "string",
                            "description": "File content"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        }
    ]

    prompt = Prompt(
        messages=[
            Message(role="user", content="请创建一个名为 test.py 的文件，内容是 print('hello')")
        ],
        tools=tools
    )

    print("\n📋 Sending prompt to model...")
    print(f"Task: 请创建一个名为 test.py 的文件")
    print(f"Tools provided: {len(tools)} tools (write_file)")
    print("="*70)

    response = await model.generate(prompt)

    print("\n📊 Model Response:")
    print(f"Content length: {len(response.content)} chars")
    print(f"Tool calls: {len(response.tool_calls)} calls")
    print("="*70)

    if response.tool_calls:
        print("\n✅ SUCCESS: Model used function calling!")
        for i, tc in enumerate(response.tool_calls, 1):
            print(f"\nTool Call {i}:")
            print(f"  Name: {tc['name']}")
            print(f"  Arguments: {tc['arguments']}")
    else:
        print("\n❌ FAIL: Model did NOT use function calling")
        print(f"\nModel returned text instead:")
        print(f"{response.content[:200]}...")

        print(f"\n⚠️  Possible reasons:")
        print(f"1. Model '{model.model_name}' doesn't support function calling")
        print(f"2. Tools parameter not passed correctly")
        print(f"3. Model ignored the tools")

        print(f"\n💡 Try switching to a model that supports function calling:")
        print(f"   - google/gemini-flash-1.5:free")
        print(f"   - meta-llama/llama-3.1-8b-instruct:free")


if __name__ == "__main__":
    asyncio.run(test_tool_use())
