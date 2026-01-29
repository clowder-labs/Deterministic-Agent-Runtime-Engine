# Design: Unified Tool Runtime via ToolManager

## Goals
- Single source of truth for active tools (visibility == invokability).
- Agent only depends on `IToolGateway` (minimal surface); no direct ToolManager usage.
- Tool providers are optional and act only as a source of tools.
- Direct tool injection remains simple and deterministic.

## Non-Goals
- Changing the five-layer orchestration semantics.
- Removing `IToolGateway` as the system-call boundary.

## Core Design
### 1) ToolManager as the core runtime registry
- ToolManager owns a `dict[capability_id, ITool]` registry (primary key is a UUID).
- Tool names are *not required* to be unique; collisions are resolved by capability id.
- ToolManager implements:
  - `IToolManager` for registration, enable/disable, metadata.
  - `IToolGateway` for invocation using the registry and envelope constraints.
- The default tool gateway instance is a ToolManager (or a thin wrapper that delegates to it).

### 2) ToolProvider becomes a tool source
- `IToolProvider.list_tools()` returns `list[ITool]` (not tool defs).
- ToolManager can register tools from providers without requiring a group identity.
- Config enable/disable applies to individual tool names or capability ids; explicit tools remain unfiltered.

### 3) Tool schemas are derived centrally
- Tool schema conversion (`ITool` → LLM tool definition) is centralized in ToolManager (or a shared factory module).
- Context assembly uses ToolManager’s registry to produce the tool list for the model.

### 4) Protocol adapter integration
- MCP/protocol adapters produce `ITool` instances (e.g., MCPToolkit) and register them into ToolManager.
- No capability-provider hop is needed.

### 5) Capability identity & LLM tool naming
- `capability_id` is the **canonical unique key** used everywhere (LLM tool name, ToolManager registry key, and ToolGateway routing key).
- Format: `tool_<uuidhex>` (e.g., `tool_4f6c2b9e3b7a4a66a1c9d2f8b5b2c9a1`), which is valid for LLM tool naming constraints and unique across tools.
- The LLM-facing tool definition uses `function.name == capability_id` so tool calls return the same identifier that ToolManager/Gateway route on.
- The original `ITool.name` is preserved in registry metadata (e.g., `display_name`) for human readability/audit and should not be relied upon for routing.

## Runtime Flow (Simplified)
1. Builder collects tools (direct + from providers).
2. Builder ensures ToolManager exists and registers tools.
3. Agent receives a reference only to `IToolGateway` (ToolManager instance).
4. Context asks ToolManager for LLM tool defs (consistent with invokable registry).
5. Tool Loop invokes `tool_gateway.invoke(...)` (delegated to ToolManager).

## Compatibility & Migration
- Provide a short-lived compatibility adapter for old provider-based registration (optional).
- Rename or deprecate `DefaultToolGateway` in favor of `ToolManager`.
- Update examples to reflect ToolManager-first usage.

## Risks
- Large surface change affecting examples, docs, and any downstream integrations.
- Removal of provider-based discovery requires new adapters for remote tools.
