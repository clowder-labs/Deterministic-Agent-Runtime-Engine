# Change: Refactor tool runtime around ToolManager + ToolGateway

## Why
Today the tool listing surface (`IToolProvider`) and the invocation surface (`IToolGateway`) can drift, allowing the model to see tools that cannot be invoked. This creates runtime failures and makes the tool subsystem harder to reason about. We want a single, trusted runtime registry that owns tool activation and invocation, while keeping the agent surface area minimal.

## What Changes
- Promote **ToolManager** to the core runtime registry and primary tool runtime implementation.
- ToolManager **implements IToolGateway** (invocation boundary) and **IToolManager** (registry management).
- **Remove `ICapabilityProvider`** from the tool runtime path; ToolManager routes directly to registered `ITool` instances via an internal tool map.
- Re-define **`IToolProvider` as a tool source** that returns `list[ITool]` for registration; tool schema conversion is centralized.
- Ensure the **LLM tool list is derived from ToolManager’s registry**, guaranteeing visibility == invokability.
- Allow **direct tool injection** into agents/builders as a first-class path (no provider required).
- Use **UUID capability ids** to avoid tool name collisions while preserving display names in metadata.

## Impact
- **Breaking API changes** in the tool interfaces (`IToolProvider`, removal of `ICapabilityProvider`, ToolManager contract changes).
- Builder, context assembly, and examples will need updates to register tools into ToolManager and to derive tool defs from ToolManager.
- MCP/protocol adapter integration must register tools as `ITool` instances instead of capability providers.
