## Context
The current builder exposes both `tool_manager` and `tool_gateway`. This makes the public API ambiguous and forces users to reason about two similar surfaces.

## Goals / Non-Goals
- Goals:
  - Expose a single tool entry point in builder: `tool_gateway`.
  - Make `IToolManager` a superset of `IToolGateway` to preserve registry+invoke in one interface.
  - Provide clear errors when tool injection requires manager capabilities.
- Non-Goals:
  - Change tool invocation semantics or registry behavior.

## Decisions
- Decision: `IToolManager` extends `IToolGateway` in the kernel.
- Decision: Builder removes `tool_manager` parameters and methods; it uses `tool_gateway` for both listing/registration and invocation.
- Decision: If tools are added and the provided gateway does not satisfy `IToolManager`, builder raises a `TypeError` with guidance.

## Risks / Trade-offs
- **Breaking change**: users supplying a gateway that is not a manager will need to upgrade or avoid `add_tools`.

## Migration Plan
1. Update kernel interface inheritance and builder signatures.
2. Update default wiring to use ToolManager as gateway.
3. Update docs/examples/tests accordingly.

## Open Questions
- None.
