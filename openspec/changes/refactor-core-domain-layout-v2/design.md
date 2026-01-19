## Context
The project is converging on the v2 Kernelized architecture (`doc/design/Architecture_Final_Review_v2.1.md`, based on v2.0). The current codebase already implements the v2 five-layer loop skeleton and core contracts, but the file layout and some contracts still reflect “transitional” choices.

This proposal captures the next structural iteration (“方案 2”):
- domain-oriented packages,
- minimal closed-loop core flow,
- complete interface surfaces with no-op permitted for non-core areas,
- and strict layering: Kernel (Layer 0) must not depend on Layer 2 implementations.

## Goals / Non-Goals
### Goals
- Adopt domain package organization for Kernel contracts + default implementations (remove the centralized `core/defaults` catch-all).
- Ensure the v2 core flow remains closed-loop and auditable (EventLog evidence, budgets, trust/policy gate, HITL wait surface).
- Ensure security-critical fields (risk/approval) are derived from trusted sources (capability registry + policy), for both plan-driven and model-driven execution.
- Keep extensibility surfaces (components + entrypoint managers) present and documented, while allowing no-op implementations.

### Non-Goals
- Backwards compatible import paths or adapter shims.
- Shipping full component manager behavior for every category (interfaces + semantics are sufficient for now).
- Building a production sandbox (stub is acceptable as long as policy is enforced before side effects).

## Current State (as implemented)
### Core contracts exist, but defaults are centralized
- Kernel contracts exist under `dare_framework/core/*` (run loop, orchestrator, execution control, context, tool gateway, security boundary, event log, budgets).
- Default implementations currently live under `dare_framework/core/defaults/*`.

### Layering leak: Kernel default imports Layer 2
`DefaultContextManager` currently imports `IMemory` from `dare_framework/components/memory/*`, which violates the desired dependency direction (Layer 0 should not depend on Layer 2). The agreed direction is to place `IMemory` in `dare_framework/contracts/` and have components implement that contract.

### Envelope inconsistency between spec and flow
In `doc/design/Architecture_Final_Review_v2.0.md` (baseline) and `doc/design/Architecture_Final_Review_v2.1.md` (current):
- The normative `Envelope` structure is boundary-only (allowed ids + budget + done predicate + risk).
- The tool loop pseudocode references `envelope.current_capability_id` and `envelope.params`.

The implementation currently mixes boundary + invocation payload in `Envelope`. The user requested to split these.

## Proposed Decisions (方案 2)
### 1) Domain packages own defaults
Each Kernel domain package SHOULD own:
- the stable contract/types (public surface)
- and its minimal default implementation (internal, dependency-injected)

This removes the need for a global `core/defaults/` directory and improves cohesion.

### 2) Entrypoint/plugin mechanism lives under `components/`
Decision: move the entrypoint-based loading system from `dare_framework/plugins/` to `dare_framework/components/` (e.g., `dare_framework/components/plugin_system/`).

Rationale:
- The mechanism exists primarily to support Layer 2 component extensibility via Python entrypoints.
- Kernel (Layer 0) still MUST NOT depend on this package; composition/builder can.

### 3) Split `Envelope` (boundary) from tool invocation payload
Introduce a separate request type (e.g., `ToolLoopRequest`) to carry:
- `capability_id`
- `params`
- `envelope` (boundary-only)

Kernel and validators SHOULD treat `capability_id`/`params` as untrusted inputs until validated/derived.

### 4) Risk/approval derivation must come from trusted registry
For both plan-driven and model-driven execution:
- `requires_approval` and `risk_level` MUST be derived from the capability registry (`IToolGateway.list_capabilities()` metadata), not from LLM-provided fields.
- The Tool Loop MUST enforce policy decisions using derived fields, and log the decision to the EventLog.

## File/Module Move Map (draft)
This is the intended direction; exact filenames can be finalized in apply stage after approval.

- Context:
  - `core/defaults/context_manager.py` → `core/context/*` (default implementation)
- Event log:
  - `core/defaults/local_event_log.py` → `core/event/*`
- Execution control (incl. HITL waiting):
  - `core/defaults/execution_control.py` → `core/execution_control/*`
- Resource/budget manager:
  - `core/defaults/resource_manager.py` → `core/budget/*`
- Tool gateway:
  - `core/defaults/tool_gateway.py` → `core/tool/*`
- Security boundary:
  - `core/defaults/security_boundary.py` → `core/security/*`
- Orchestrator:
  - `core/defaults/loop_orchestrator.py` → `core/orchestrator/*`
- Run loop:
  - `core/defaults/run_loop.py` → `core/run_loop/*`
- Extension point (hooks registry):
  - `core/defaults/extension_point.py` → `core/hook/*`

## Risks / Trade-offs
- Large import-path churn (acceptable; compatibility is out of scope).
- Moving modules into packages may require renaming existing `*.py` modules to avoid package/module name conflicts (e.g., `core/budget.py` vs `core/budget/`).
- Tool loop request split is a contract change and must be applied consistently across validator/tool gateway/orchestrator/tests.

## Confirmed Decisions (before apply)
1) Entrypoint/plugin discovery code moves under `dare_framework/components/` (target: `dare_framework/components/plugin_system/`).
2) Prefer “clean” domain packaging: convert top-level Kernel modules (e.g., `core/budget.py`) into domain packages where appropriate.
3) Do not edit `doc/design/Architecture_Final_Review_v2.0.md`; create `doc/design/Architecture_Final_Review_v2.1.md` and place adjustments there.
