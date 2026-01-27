## Context
V4 requires a trusted registry for tool metadata (risk, approval, timeouts) and a clear boundary between registration, prompt exposure, and invocation. ToolGateway is the side‑effect boundary, but a Tool Manager is needed to own registry state and to provide prompt tool definitions traceable to trusted metadata.

## Goals / Non-Goals
- Goals:
  - Define a complete Tool Manager contract that owns registry state and prompt tool definitions.
  - Ensure capability identity and metadata are stable and trusted.
  - Keep ToolGateway as the only execution boundary for side‑effects.
- Non-Goals:
  - Implement protocol adapter discovery or remote capability execution.
  - Change ToolGateway invocation semantics.

## Decisions
- Tool Manager owns a trusted capability registry and exports tool definitions for prompt assembly.
- Tool Manager aggregates ICapabilityProvider instances but does not invoke tools.
- Capability identity uses a stable namespace + name (+ optional version) scheme.
- Trusted metadata (risk/approval/timeout/work_unit) originates from Tool Manager registry, not model output.

## Risks / Trade-offs
- Registry duplication risk if providers also cache capability state.
  - Mitigation: define Tool Manager as source of truth and refresh providers into registry.
- Backwards compatibility with existing examples.
  - Mitigation: keep ToolGateway flow intact; Tool Manager feeds prompt tools only.

## Migration Plan
1. Add Tool Manager interface and implementation.
2. Wire Tool Manager into builder/context tool listing.
3. Update tests/examples to use Tool Manager for tool listing when needed.

## Open Questions
- Should Tool Manager enforce capability id format or allow custom policies?
- Should Tool Manager persist registry snapshots for audit beyond runtime memory?
