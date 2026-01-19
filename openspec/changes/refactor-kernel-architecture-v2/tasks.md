## 1. Implementation
- [x] 1.1 Audit current v1.3 runtime/interfaces and map each responsibility to v2.0 Kernel/Adapter/Component layers (record findings in `design.md` if adjustments are needed).
- [x] 1.2 Define v2 canonical data models (`CapabilityDescriptor`, `CapabilityType`, `Budget`, `Envelope`, `Checkpoint`, `ContextPacket`, v2 run/results/state view) with strict typing.
- [x] 1.3 Define v2 Kernel protocols (`IRunLoop`, `ILoopOrchestrator`, `IExecutionControl`, `IContextManager`, `IResourceManager`, `IEventLog` v2, `IToolGateway`, `ISecurityBoundary`, `IExtensionPoint`).
- [x] 1.4 Implement a minimal `IEventLog` v2 adapter over the existing append-only hash-chained local event log, including `query` and a minimal `replay` contract.
- [x] 1.5 Implement `IResourceManager` MVP (tool-calls/time budgets first) and wire `check_limit()` into Plan/Execute/Tool loops.
- [x] 1.6 Implement `IExecutionControl` MVP (`poll_or_raise`, `pause`, `resume`, `checkpoint`) with event log evidence; checkpoint persistence MAY be file-based initially.
- [x] 1.7 Implement `ISecurityBoundary` as a composable façade (trust + policy + sandbox stub). Enforce fail-closed defaults for high-risk or ambiguous actions.
- [x] 1.8 Implement `IToolGateway` with a provider registry, capability listing, and invocation as the only side-effect boundary.
- [x] 1.9 Implement the Tool Loop using `Envelope` + `DonePredicate`, recording evidence and budget consumption to the event log.
- [x] 1.10 Implement `IContextManager` MVP: support `assemble(PLAN/EXECUTE)` and log attribution; implement `compress/retrieve/ensure_index/route` as no-op or empty-return (but still wired and auditable).
- [x] 1.11 Implement `ILoopOrchestrator` (five-layer skeleton) using the above Kernel components, including Plan attempt isolation and the HITL gate between Plan and Execute.
- [x] 1.12 Implement `IRunLoop` as a tick-based wrapper over the orchestrator, exposing `state` and `tick()` for debugging/visualization.
- [x] 1.13 Refactor the Developer API (AgentBuilder/composition) to build the v2 Kernel + components, expose `with_kernel_defaults()` / `with_budget(...)` / `with_protocol(...)`, and remove the v1.3 runtime as the primary execution surface (**BREAKING**).
- [x] 1.14 Define Layer 1 protocol adapter contracts (`IProtocolAdapter`) and implement an MVP MCP adapter integration path that registers discovered tool capabilities via providers into `IToolGateway`.
- [x] 1.15 Update examples and tests to use v2.0 APIs and validate an end-to-end deterministic run (closed loop with event log evidence).
- [x] 1.16 Add unit/integration tests for: plan isolation, tool loop done predicate + budget, HITL pause/resume path, event log chain/replay, and optional protocol adapter behavior.

## 2. Validation
- [x] 2.1 Run `ruff`, `black --check`, `mypy --strict`, and `pytest`; fix failures introduced by the refactor. (pytest run; ruff/black/mypy not installed in this environment)
