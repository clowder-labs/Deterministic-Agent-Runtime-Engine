## 1. OpenSpec artifacts and scope

- [x] 1.1 Create proposal/design/spec deltas for full review + security canonicalization.
- [x] 1.2 Validate change artifacts with strict OpenSpec validation.
- [x] 1.3 Sync finalized delta requirements into main specs.

## 2. Design documentation full review

- [x] 2.1 Review `docs/design/Architecture.md` and correct stale runtime-state assertions.
- [x] 2.2 Review and update core module docs (`plan/tool/security/agent`) to match implementation baseline.
- [x] 2.3 Generate full review gap analysis and TODO documents under `docs/todos/`.

## 3. Security boundary canonicalization

- [x] 3.1 Remove compatibility shim exports for `DefaultSecurityBoundary` under `dare_framework/security/impl/`.
- [x] 3.2 Migrate all in-repo imports to canonical path (`dare_framework.security`).
- [x] 3.3 Update docs to remove compatibility-path references.

## 4. Verification and evidence

- [x] 4.1 Run targeted tests for security boundary and step-driven execution.
- [x] 4.2 Verify no residual compatibility imports and record evidence in TODO artifacts.
