## Why

`ISecurityBoundary` is currently defined but not enforced end-to-end in canonical runtime paths. Without runtime integration, trust derivation and policy decisions remain advisory and cannot block unsafe plan/tool execution.

## What Changes

- Add a canonical default `DefaultSecurityBoundary` implementation for the security domain.
- Integrate security policy gate at Plan->Execute entry in `DareAgent`.
- Integrate trust derivation + policy gate + sandboxed execution wrapper at Tool Loop entry in `DareAgent`.
- Add unit tests that verify deny/approve_required/allow behavior and trusted parameter propagation.
- Add compatibility export path for legacy `security.impl.default_security_boundary` imports.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `define-trust-boundary`: require concrete default boundary behavior and canonical export.
- `core-runtime`: require `DareAgent` to enforce security gate at plan entry and tool invocation entry.

## Impact

- Affected code:
  - `dare_framework/security/**`
  - `dare_framework/agent/dare_agent.py`
  - `tests/unit/test_dare_agent_security_boundary.py`
- API impact:
  - Additive constructor injection for `DareAgent(security_boundary=...)`; default remains backward compatible.
- Behavior impact:
  - Runtime now blocks execution when security policy returns `DENY` or `APPROVE_REQUIRED` without an approval bridge.
