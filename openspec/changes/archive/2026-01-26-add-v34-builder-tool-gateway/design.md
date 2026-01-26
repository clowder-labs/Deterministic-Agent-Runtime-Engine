## Context
The canonical `dare_framework` package is now the v3.4 context-centric baseline, but it lacks a builder and default tool gateway. This blocks incremental migration of examples/tests and violates the v4 interface intent that tool definitions originate from a trusted registry (`IToolGateway.list_capabilities()`).

## Goals / Non-Goals
- Goals:
  - Provide a minimal AgentBuilder that composes a v3.4 SimpleChatAgent with context, model adapter, budget, and tool wiring.
  - Provide a default IToolGateway implementation and gateway-backed tool provider for Context assembly.
  - Provide an in-process capability provider for local ITool instances with optional metadata extraction.
  - Add unit tests to exercise the baseline builder/gateway behavior.
- Non-Goals:
  - Full v2 runtime orchestration (plan/execute/tool loops, HITL gating, event log).
  - Entry point discovery/managers or compatibility wrappers for archived v2/v3 APIs.
  - MCP adapter implementations beyond interface coverage.

## Decisions
- **Baseline builder only**: Implement a minimal AgentBuilder that returns a `SimpleChatAgent` and focuses on context/model/tool wiring (no planner/validator/remediator yet).
- **Gateway-backed tool defs**: Provide an `IToolProvider` implementation that derives tool definitions from `IToolGateway.list_capabilities()` to satisfy the trust boundary requirement.
- **In-process tool provider**: Add a lightweight `ICapabilityProvider` that wraps local `ITool` instances and uses optional metadata attributes (description, schemas, risk fields) when present, with safe defaults otherwise.

## Alternatives Considered
- **Compatibility wrapper for v2 AgentBuilder**: Rejected because the project explicitly does not want compatibility layers and aims to converge on v3.4 semantics.
- **Reintroduce full v2 runtime**: Rejected as too large for the first incremental step; it will be staged in later changes.

## Risks / Trade-offs
- Minimal tool metadata may produce limited tool definitions until v3.4 tools provide richer schemas/metadata.
- AgentBuilder returning SimpleChatAgent does not exercise tool invocation yet; further runtime work is required to restore full tool loop behavior.

## Migration Plan
1. Land minimal builder/gateway implementations.
2. Update or add unit tests to validate builder + gateway behavior.
3. Gradually unskip/migrate legacy tests once additional runtime components are implemented.

## Open Questions
- Should we introduce a stricter tool metadata protocol (e.g., optional Protocol with `description`, `input_schema`, `output_schema`, `risk`), or rely on duck-typing with defaults?
- Should the built agent expose `tool_gateway` for debugging in early iterations?
