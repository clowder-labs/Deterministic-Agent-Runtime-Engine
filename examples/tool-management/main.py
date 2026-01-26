"""Tool Management Example.

This example demonstrates the tool management capabilities of dare_framework.
Aligned with the v4 tool runtime configuration used in examples/base_tool.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path for local development
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.plan import Envelope
from dare_framework.tool import (
    DefaultExecutionControl,
    DefaultToolGateway,
    EchoTool,
    GatewayToolProvider,
    NativeToolProvider,
    NoopTool,
    RunContextState,
)

# Configuration (consistent with examples/base_tool)
WORKSPACE_ROOT = os.getenv("TOOL_WORKSPACE_ROOT", ".")


async def main():
    """Demonstrate tool management features."""
    
    print("=" * 60)
    print("DARE Framework v4 - Tool Management Example")
    print("=" * 60)
    
    # 1. Create components
    print("\n[1] Creating components...")
    run_context = RunContextState(
        config={
            "workspace_roots": [WORKSPACE_ROOT],
        }
    )

    gateway = DefaultToolGateway()
    execution_control = DefaultExecutionControl()
    tools = [NoopTool(), EchoTool()]
    provider = NativeToolProvider(tools=tools, context_factory=run_context.build)
    
    # 2. Register tools with the provider
    print("\n[2] Registering tools...")
    print(f"    Registered tools: noop, echo")
    
    # 3. Register provider with gateway
    print("\n[3] Registering provider with gateway...")
    gateway.register_provider(provider)
    
    # 4. List capabilities
    print("\n[4] Listing capabilities from gateway...")
    capabilities = await gateway.list_capabilities()
    for cap in capabilities:
        print(f"    - {cap.name}: {cap.description}")
        if cap.metadata:
            print(f"      risk_level: {cap.metadata.get('risk_level')}")
            print(f"      requires_approval: {cap.metadata.get('requires_approval')}")
    
    # 5. Check provider health
    print("\n[5] Checking provider health...")
    health = await gateway.health_check()
    for provider_id, status in health.items():
        print(f"    {provider_id}: {status.value}")
    
    # 6. Invoke tools through gateway
    print("\n[6] Invoking tools...")
    
    # Create an envelope (execution boundary)
    envelope = Envelope(allowed_capability_ids=["tool:noop", "tool:echo"])
    
    # Invoke noop tool
    print("\n    Invoking 'noop'...")
    result = await gateway.invoke("tool:noop", {}, envelope=envelope)
    print(f"    Result: success={result.success}, output={result.output}")
    
    # Invoke echo tool
    print("\n    Invoking 'echo' with message='Hello, DARE!'...")
    result = await gateway.invoke("tool:echo", {"message": "Hello, DARE!"}, envelope=envelope)
    print(f"    Result: success={result.success}, output={result.output}")
    
    # 7. Demonstrate envelope restrictions
    print("\n[7] Demonstrating envelope restrictions...")
    restricted_envelope = Envelope(allowed_capability_ids=["tool:noop"])  # echo not allowed
    
    try:
        await gateway.invoke("tool:echo", {"message": "test"}, envelope=restricted_envelope)
    except PermissionError as e:
        print(f"    Expected error: {e}")
    
    # 8. Demonstrate execution control
    print("\n[8] Demonstrating execution control...")
    
    # Create a checkpoint
    checkpoint_id = await execution_control.checkpoint("demo", {"action": "test"})
    print(f"    Created checkpoint: {checkpoint_id[:8]}...")
    
    # Pause execution
    pause_checkpoint = await execution_control.pause("User requested pause")
    print(f"    Paused with checkpoint: {pause_checkpoint[:8]}...")
    print(f"    Current signal: {execution_control.poll().value}")
    
    # Resume execution
    await execution_control.resume(pause_checkpoint)
    print(f"    Resumed, signal: {execution_control.poll().value}")
    
    # 9. Get LLM-compatible tool definitions
    print("\n[9] Getting LLM-compatible tool definitions...")
    tool_provider = GatewayToolProvider(gateway)
    await tool_provider.refresh()
    tool_defs = tool_provider.list_tools()
    for tool_def in tool_defs:
        func = tool_def["function"]
        print(f"    - {func['name']}: {func['description'][:50]}...")
    
    # 10. Dynamic tool management
    print("\n[10] Demonstrating dynamic tool management...")
    print(f"    Tools before unregister: {len(await provider.list())}")
    provider.unregister_tool("noop")
    print(f"    Tools after unregister 'noop': {len(await provider.list())}")
    provider.register_tool(NoopTool())
    print(f"    Tools after re-register: {len(await provider.list())}")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
