## Context
The current codebase implements a v1.3-shaped runtime (`IRuntime` + `AgentRuntime`) and related contracts (`IContextAssembler`, `IToolRuntime`, `ICheckpoint`, `IPolicyEngine`, `ITrustBoundary`). The v2.0 architecture (`doc/design/Architecture_Final_Review_v2.0.md`) reorganizes the framework into a 4-layer model and introduces a Kernel contract that standardizes:

- Scheduling as immutable infrastructure (`IRunLoop`, `ILoopOrchestrator`)
- Context engineering as a first-class control plane (`IContextManager`)
- Budget/resource control (`IResourceManager`)
- Long-task pause/resume/checkpoint via a unified control plane (`IExecutionControl`)
- A system-call boundary for all side effects (`IToolGateway`)
- A composable security boundary (`ISecurityBoundary = trust + policy + sandbox`)
- Protocol-agnostic capability discovery/invocation via Layer 1 protocol adapters

The implementation MUST be refactored to conform to the v2.0 contracts and execution flow. Compatibility with the v1.3 API is explicitly out of scope.

## Goals / Non-Goals
- Goals:
  - Align public contracts and core flow with v2.0 (Kernel + Protocol Adapters + Components + Developer API).
  - Preserve the five-layer loop as the framework “skeleton” while making it explicit via `ILoopOrchestrator`.
  - Ensure a closed loop: plan isolation, tool loop with done predicate, event logging, and a minimal pause/resume path.
  - Provide complete interface surfaces; allow no-op implementations for non-core methods as a temporary scaffold.
  - Follow `doc/guides/Development_Constraints.md`: minimal coupling, dependency injection, append-only audit, tests, structured logging.
- Non-Goals:
  - Backwards compatible import paths or API shims for v1.3.
  - A production-grade sandbox on day 1 (allowed: minimal stub that is fail-closed for high-risk).
  - Full A2A/A2UI implementation (capability types may exist, but initial implementation focuses on tools).

## Decisions
### 1) Package layering in code
Keep the existing “core vs components vs composition” repository shape, but re-map it to v2 layers:
- Layer 0 (Kernel): `dare_framework/core/kernel/*` (contracts + default implementations)
- Layer 1 (Protocol Adapters): `dare_framework/protocols/*` (adapters that translate protocol world → canonical capability descriptors)
- Layer 2 (Pluggable Components): `dare_framework/components/*` (strategies and capability providers; includes no-op defaults)
- Layer 3 (Developer API): `dare_framework/builder.py` (+ composition managers where still useful)

### 2) Core flow definition (“core vs no-op”)
The initial v2 “core flow” is:
- `ILoopOrchestrator`: Session → Milestone → Plan → Execute → Tool
- `IContextManager.assemble()` for `PLAN` and `EXECUTE` stages
- `ISecurityBoundary.verify_trust()` + `check_policy()` around plan execution and tool invocation
- `IToolGateway.invoke()` as the only side-effect boundary, with the Tool Loop enforcing Envelope + DonePredicate
- `IEventLog.append()` for all critical boundaries (plan attempts, approvals, tool calls, verification)

Everything else MAY be no-op initially but MUST exist and be called from the orchestrator at the correct boundary:
- `IContextManager.retrieve/ensure_index/route/compress`
- sandbox execution in `ISecurityBoundary.execute_safe`
- non-tool capability types (`AGENT`, `UI`)

### 3) Capability model unification
Adopt v2 canonical types:
- `CapabilityDescriptor` + `CapabilityType`
- `Envelope` (allowed_capability_ids + `Budget` + `DonePredicate` + risk level)
- `Budget` (tokens/cost/time/tool_calls)

Existing v1.3 models (`EnvelopeBudget`, `Envelope.allowed_tools`) will be replaced or refactored accordingly.

### 4) Security boundary composition
Implement `ISecurityBoundary` as a thin façade composed of:
- trust derivation (v1.3 `ITrustBoundary` semantics)
- policy decision (v1.3 `IPolicyEngine` semantics)
- sandbox execution (stubbed initially; fail-closed for high-risk or unknown actions)

This keeps the Kernel API small while allowing independent evolution of trust/policy/sandbox.

## Flow sketch (normative reference)
The orchestrator follows the v2.0 pseudocode shapes:
- Plan Loop isolates failed attempts from milestone state.
- HITL gate is between Plan and Execute.
- Tool Loop retries until DonePredicate is satisfied or budget is exhausted.

## Suggestions / items to confirm during implementation
The v2.0 document leaves several “needs iteration” items; this change proposal will make explicit initial decisions:
- Support only `CapabilityType.TOOL` in the first implementation; keep `AGENT/UI` descriptors but return `NotImplemented` on invocation.
- Define a minimal `SandboxSpec` that allows an “unsafe” path only when policy allows and risk is low; otherwise require approval or deny.
- Define a minimal `RuntimeStateView` payload schema for context assembly (task/milestone summary, last tool evidence, errors, budgets).
- Standardize event payload correlation fields (`task_id`, `session_id`, `milestone_id`, `run_id`, `checkpoint_id`, `capability_id`).

## Risks / Trade-offs
- Broad breaking changes across `dare_framework/*` and examples/tests.
- Temporary no-op surfaces can mask missing behaviors; mitigated by interface-level tests and explicit event logging of no-op paths.
- Increased up-front contract surface; mitigated by strict layering (Kernel does not import components) and minimal default implementations.

