# Change: Refactor framework to the v2.0 kernelized architecture

## Why
`doc/design/archive/Architecture_Final_Review_v2.0.md` updates the framework architecture to a kernelized, protocol-agnostic, context-engineering-first design. The current implementation is aligned with the v1.3 runtime shape (monolithic `IRuntime` + `IToolRuntime` + `IContextAssembler` + `ICheckpoint`), which diverges from the v2.0 contracts and execution flow.

The project goal is to make the implementation conform to the v2.0 architecture (no backwards-compatibility required) and ensure an end-to-end closed loop with complete interfaces. Non-core interfaces MAY be implemented as no-ops initially, but must exist and be correctly wired into the core loop.

## What Changes
- Introduce Layer 0 (Kernel) contracts and default implementations per v2.0:
  - `IRunLoop` (tick-based state machine), `ILoopOrchestrator` (five-layer skeleton)
  - `IExecutionControl` (pause/resume/checkpoint), `IResourceManager` (budgets)
  - `IContextManager` (assemble/ compress / retrieve / ensure_index / route)
  - `IToolGateway` (system-call boundary), `ISecurityBoundary` (trust/policy/sandbox, composable)
  - `IEventLog` v2 surface (append/query/replay/verify), `IExtensionPoint` (hooks)
- Replace the v1.3 runtime orchestration surface (`IRuntime`) with the v2.0 Kernel flow (`IRunLoop` + `ILoopOrchestrator`).
- Refactor tool execution to route all side effects through `IToolGateway`, with capability providers as the source of tools (native + protocol).
- Introduce Layer 1 (Protocol Adapters) interfaces and an initial `MCPAdapter` integration path that translates protocol capabilities into canonical `CapabilityDescriptor`s.
- Update the developer API (AgentBuilder / composition) to assemble v2 Kernel + components + optional protocol adapters, with explicit budget configuration.
- Provide no-op (or minimal fail-closed) implementations for non-core surfaces in the initial iteration: `IContextManager.route`, `IContextManager.ensure_index`, sandbox execution, UI/agent capabilities.
- Update examples/tests to validate the v2 closed-loop end-to-end path using deterministic/mock components.

## Impact
- Affected specs: `core-runtime`, `interface-layer`, `protocol-adapters`, `example-agent` (v2 rewrites, **BREAKING**).
- Affected code: `dare_framework/core/*`, `dare_framework/components/*`, `dare_framework/builder.py`, `examples/*`, `tests/*`.
- References:
  - `doc/design/archive/Architecture_Final_Review_v2.0.md` (authoritative)
  - `doc/guides/Development_Constraints.md` (implementation principles)
