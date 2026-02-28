## 1. Security boundary baseline

- [x] 1.1 Add a canonical default `ISecurityBoundary` implementation under `dare_framework/security`.
- [x] 1.2 Add compatibility export path for legacy `security.impl.default_security_boundary` imports.
- [x] 1.3 Add/adjust facade exports for default boundary usage in canonical runtime.

## 2. DareAgent runtime integration

- [x] 2.1 Add `security_boundary` injection to `DareAgent` with default fallback behavior.
- [x] 2.2 Enforce plan-entry policy gate (`execute_plan`) before Execute Loop.
- [x] 2.3 Enforce tool-entry trust derivation + policy gate + safe execution wrapper.

## 3. Verification

- [x] 3.1 Add failing unit tests for deny/approve/trust-rewrite/plan-gate behavior.
- [x] 3.2 Implement minimal runtime changes to make new tests pass.
- [x] 3.3 Run targeted regression tests for affected DareAgent execution paths.
- [x] 3.4 Update DG-004 TODO evidence and status after verification.
