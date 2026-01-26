# Tool Management Example

This example demonstrates the tool management capabilities of `dare_framework3_4`.

## Features Demonstrated

1. **Gateway & Provider Setup** - Creating and connecting `DefaultToolGateway` with `NativeToolProvider`
2. **Tool Registration** - Dynamically registering `NoopTool` and `EchoTool`
3. **Capability Discovery** - Listing capabilities with trusted metadata
4. **Health Checking** - Monitoring provider health status
5. **Tool Invocation** - Invoking tools through the gateway with envelope boundaries
6. **Envelope Restrictions** - Demonstrating capability allow-lists
7. **Execution Control** - Using checkpoints, pause, and resume for HITL
8. **LLM-Compatible Definitions** - Getting tool definitions for function-calling
9. **Dynamic Management** - Register/unregister tools at runtime

## Running the Example

```bash
cd /path/to/Deterministic-Agent-Runtime-Engine
python examples/tool-management/main.py
```

## Real Model Tool-Chat Example

This example mirrors the `examples/base_tool` tool chat flow and uses a real model adapter.

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

[3] Registering provider with gateway...

[4] Listing capabilities from gateway...
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
