# Change: add V4 tool manager capability

## Why
V4 requires a trusted capability registry and explicit tool management boundaries. Today the design describes ToolGateway and providers, but it lacks a complete Tool Manager capability that owns registry, metadata, and prompt tool definitions. This change formalizes the Tool Manager contract so V4 policy, trust boundary, and tool registration are coherent and auditable.

## What Changes
- Define a complete `IToolManager` contract in the tool domain (registry, provider aggregation, tool definition export).
- Specify Tool Manager responsibilities for trusted metadata, capability identity, and enable/disable controls.
- Clarify that Tool Manager produces prompt tool definitions but never executes tools (ToolGateway remains the side‑effect boundary).
- Update manager interface ownership paths to the non-versioned `dare_framework` package.

## Impact
- Affected specs: `interface-layer`, `component-management`
- Affected code (future): `dare_framework/tool/interfaces.py`, `dare_framework/tool/_internal/managers/*`, `dare_framework/tool/__init__.py`, builder/context wiring, tests
