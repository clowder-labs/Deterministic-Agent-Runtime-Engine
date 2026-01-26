# Change: Add v3.4 AgentBuilder + ToolGateway baseline

## Why
The canonical `dare_framework` package (v3.4 context-centric) currently lacks a builder and default tool gateway, so examples/tests are skipped and migration from archived v2/v3 code cannot proceed. We need a minimal, v3.4-aligned composition API and tool gateway to begin gradual convergence.

## What Changes
- Add a minimal `AgentBuilder` (or equivalent) in the canonical package that composes a v3.4 `SimpleChatAgent` with context, model adapter, budget, and tool provider wiring.
- Provide a default `IToolGateway` implementation plus a gateway-backed `IToolProvider` to expose tool definitions derived from `list_capabilities()` (trust boundary requirement).
- Add an in-process `ICapabilityProvider` that wraps local `ITool` instances into `CapabilityDescriptor`s with optional metadata extraction.
- Add focused unit tests validating builder composition, tool gateway capability aggregation, and tool definition derivation.

## Impact
- Affected specs: `interface-layer`
- Affected code: `dare_framework/builder`, `dare_framework/tool/_internal`, `dare_framework/context`, `tests/unit`

## Out of Scope
- Full v2 runtime/orchestrator, entrypoint managers, or compatibility wrappers for archived APIs
- MCP integration flows beyond existing interfaces

## Open Questions
- Which tool metadata fields should be mandatory vs optional when adapting `ITool` → `CapabilityDescriptor`?
- Should the initial AgentBuilder expose `tool_gateway` on the built agent for debugging/inspection?
