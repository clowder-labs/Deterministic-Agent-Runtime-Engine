## Context
The runtime currently allows `ToolManager` to be used directly as an invocation gateway. Although functionally convenient, it blurs lifecycle responsibilities (registration, enablement, provider refresh) with side-effect execution concerns.

## Goals / Non-Goals
- Goals:
  - Keep tool lifecycle in `ToolManager` only.
  - Keep invocation and envelope allowlisting in `ToolGateway` only.
  - Preserve builder ergonomics by still allowing custom manager injection.
- Non-Goals:
  - Redesign provider discovery.
  - Change envelope semantics or tool execution payload shape.

## Decisions
- Decision: `ToolManager` implements only `IToolManager`.
- Decision: `ToolGateway` accepts `IToolManager` and performs capability invocation through `get_tool(...)`.
- Decision: Builder always returns `(ToolGateway(tool_manager), tool_manager)`.

## Risks / Trade-offs
- **Breaking behavior**: call sites that invoked `ToolManager.invoke(...)` must switch to `ToolGateway`.
- **Extra object**: runtime now always has two objects (manager + gateway), which is slightly more wiring but clearer ownership.

## Migration Plan
1. Remove gateway inheritance and invoke method from `ToolManager`.
2. Ensure `ToolGateway` depends on `IToolManager`, not concrete `ToolManager`.
3. Update builder fallback logic to always wrap manager with gateway.
4. Update tests that previously invoked manager directly.

## Open Questions
- Should builder expose both `with_tool_manager(...)` and `with_tool_gateway(...)` APIs explicitly for naming clarity in a follow-up change?
