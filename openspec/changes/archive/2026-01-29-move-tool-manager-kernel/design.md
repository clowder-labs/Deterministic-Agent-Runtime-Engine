## Context
The tool runtime now treats `ToolManager` as the registry and invocation surface. The extra `DefaultToolGateway` wrapper is redundant and obscures the core boundary. `IToolManager` currently lives in `tool/interfaces.py`, which suggests it is pluggable, but it functions as a kernel-level contract.

## Goals / Non-Goals
- Goals:
  - Place `IToolManager` in the tool kernel to reflect its core role.
  - Remove `DefaultToolGateway` and use `ToolManager` directly as the default `IToolGateway`.
  - Keep public API usage simple: `ToolManager` for registration + invocation.
- Non-Goals:
  - Redesign tool provider semantics.
  - Change tool invocation behavior beyond the relocation/removal above.

## Decisions
- Decision: Define `IToolManager` in `dare_framework/tool/kernel.py` and remove it from `tool/interfaces.py`.
- Decision: Remove `DefaultToolGateway` and update callers to construct `ToolManager` directly.
- Decision: Do not add inheritance between `IToolManager` and `IToolGateway`; implementations may implement both.

## Risks / Trade-offs
- **Breaking imports**: downstream code importing `IToolManager` from `tool.interfaces` will break.
- **Removal of class**: `DefaultToolGateway` imports will break and need updates.

## Migration Plan
1. Move `IToolManager` to kernel, update `__init__.py` exports.
2. Remove `DefaultToolGateway` and replace usage with `ToolManager`.
3. Update tests/examples/docs and verify imports compile.

## Open Questions
- None.
