## Context

The canonical `dare_framework` runtime defines `ISecurityBoundary` and related types, but `DareAgent` did not apply this boundary before plan execution or tool invocation. As a result, policy decisions could not enforce runtime behavior, and trust derivation outputs were not consumed by tool execution.

This change targets `DG-004` and keeps existing default behavior stable by introducing a permissive default boundary while enabling explicit policy enforcement for injected/custom boundaries.

## Goals / Non-Goals

**Goals:**
- Provide a default concrete implementation of `ISecurityBoundary`.
- Enforce security policy checks at plan entry (before Execute Loop).
- Enforce trust derivation + policy gate + safe execution wrapper at tool entry.
- Preserve backward compatibility for existing code paths and builder behavior.

**Non-Goals:**
- No full HITL approval bridge implementation for `APPROVE_REQUIRED`.
- No redesign of risk-level derivation in validator/tool registry.
- No policy engine DSL or external policy backend integration.

## Decisions

### Decision 1: Default boundary is permissive but structured

- `DefaultSecurityBoundary`:
  - normalizes trust input (`verify_trust`)
  - returns `ALLOW` by default (`check_policy`)
  - wraps sync/async calls via `execute_safe`

Rationale:
- preserves current runtime behavior while making boundary invocation mandatory.

### Decision 2: Plan entry gate in milestone loop

- Add policy check before Execute Loop with action `execute_plan`.
- On `DENY`/`APPROVE_REQUIRED`, milestone returns failure immediately with explicit error.

Rationale:
- fail-fast at boundary crossing; avoid executing model/tool paths when policy forbids it.

### Decision 3: Tool entry uses trusted params and safe wrapper

- In Tool Loop:
  - derive trusted input via `verify_trust`
  - run `check_policy(action="invoke_tool")`
  - execute gateway call through `execute_safe`
- Approved tool calls use trusted params (not raw model params).

Rationale:
- ensures trust derivation has runtime effect and enforces policy prior to side effects.

## Risks / Trade-offs

- [Risk] `APPROVE_REQUIRED` currently maps to runtime failure without HITL bridge.  
  -> Mitigation: explicit error text; follow-up change can integrate execution-control wait/resume semantics.

- [Risk] Additional policy checks may impact hot-path latency.  
  -> Mitigation: default boundary logic is minimal and O(1).

- [Risk] Legacy imports may break if default class path changes.  
  -> Mitigation: provide compatibility shim under `dare_framework/security/impl/default_security_boundary.py`.

## Migration Plan

1. Add default boundary implementation and compatibility exports.
2. Add failing security-boundary runtime tests (deny/approve/trust rewrite/plan gate).
3. Integrate plan and tool entry gating in `DareAgent`.
4. Re-run targeted unit tests and update TODO/OpenSpec task states.

Rollback:
- Revert runtime policy checks and keep interface-only boundary definitions.

## Open Questions

- Should `APPROVE_REQUIRED` be wired to `IExecutionControl.pause()/wait_for_human()/resume()` in canonical runtime?
- Should policy decisions be emitted with a standardized event taxonomy beyond current `security.*` events?
