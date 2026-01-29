# Change: Unify tool gateway surface in builders

## Why
Exposing both `tool_manager` and `tool_gateway` in the builder is confusing for users and implies two entry points for tool orchestration. A single `tool_gateway` surface is clearer and aligns with the “system-call boundary” mental model.

## What Changes
- **BREAKING** Remove `tool_manager` from builder APIs and keep only `tool_gateway`.
- **BREAKING** Make `IToolManager` inherit from `IToolGateway` so the default gateway supports registry + invocation.
- Builder will require an `IToolManager`-compatible gateway when tools are injected; otherwise it raises a clear error.

## Impact
- Affected specs: `interface-layer`, `component-management`
- Affected code: `dare_framework/tool/kernel.py`, `dare_framework/builder/builder.py`, docs/tests/examples
