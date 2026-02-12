# Change: Separate Tool Manager lifecycle from Tool Gateway invocation

## Why
`ToolManager` currently owns both capability lifecycle and runtime invocation, which conflates two distinct boundaries. This makes custom manager injection less explicit and weakens the "all side-effects flow through gateway" mental model.

## What Changes
- **BREAKING** Remove `IToolGateway` implementation from default `ToolManager`.
- Keep `ToolManager` focused on trusted capability registry and provider/tool lifecycle.
- Make `ToolGateway` the explicit invocation boundary that delegates capability lookup to an injected `IToolManager`.
- Update builder wiring to always compose `ToolGateway(tool_manager)` rather than using manager-as-gateway fallback.
- Update unit tests to validate the separated responsibilities.

## Impact
- Affected specs: `interface-layer`, `component-management`
- Affected code: `dare_framework/tool/tool_manager.py`, `dare_framework/tool/tool_gateway.py`, `dare_framework/agent/builder.py`, tool gateway/manager unit tests
