# Change: Move ToolManager interface to kernel and remove DefaultToolGateway

## Why
Tool management is a core runtime boundary. Placing `IToolManager` in the kernel aligns it with other stable interfaces and removes the redundant `DefaultToolGateway` wrapper so the gateway surface is simpler and unambiguous.

## What Changes
- **BREAKING** Move `IToolManager` from `dare_framework.tool.interfaces` to `dare_framework.tool.kernel` and update all imports/exports.
- **BREAKING** Remove `DefaultToolGateway`; use `ToolManager` as the default `IToolGateway` implementation.
- Update docs, examples, and tests to reference the new import path and gateway type.

## Impact
- Affected specs: `interface-layer`
- Affected code: `dare_framework/tool/kernel.py`, `dare_framework/tool/interfaces.py`, `dare_framework/tool/__init__.py`, tool manager/gateway internals, builders, context, examples, tests, docs
