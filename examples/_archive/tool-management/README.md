# Tool Management Example (BaseAgent Builder-Based)

This example demonstrates the tool management capabilities of `dare_framework` with builder-based assembly.

## Features Demonstrated

1. **Builder Assembly** - Building the agent shell via BaseAgent builders while injecting a ToolManager-backed gateway
2. **Gateway Setup** - Creating `ToolManager` as the default gateway
3. **Tool Registration** - Dynamically registering `NoopTool` and `EchoTool`
4. **Capability Discovery** - Listing capabilities with trusted metadata
5. **Health Checking** - Monitoring registry/provider health status
6. **Tool Invocation** - Invoking tools through the gateway with envelope boundaries
7. **Envelope Restrictions** - Demonstrating capability allow-lists
8. **Execution Control** - Using checkpoints, pause, and resume for HITL
9. **LLM-Compatible Definitions** - Getting tool definitions for function-calling
10. **Dynamic Management** - Register/unregister tools at runtime

## Running the Example

```bash
cd /path/to/Deterministic-Agent-Runtime-Engine
python examples/tool-management/main.py
```

## Real Model Tool-Chat Example

This example mirrors the `examples/base_tool` tool chat flow and uses a real model adapter with builder wiring.

```bash
python examples/tool-management/tool_chat.py
```

## Expected Output

```
============================================================
DARE Framework v4 - Tool Management Example
============================================================

[1] Creating components...

[2] Registering tools...
    Registered tools: noop, echo

[3] Listing capabilities from gateway...
    - noop: A no-operation tool that does nothing and always succeeds.
      risk_level: read_only
      requires_approval: False
    - echo: Echoes back the input message.
      risk_level: read_only
      requires_approval: False

...

============================================================
Example completed successfully!
============================================================
```
