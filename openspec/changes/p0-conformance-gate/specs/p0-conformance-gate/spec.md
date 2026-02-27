## ADDED Requirements

### Requirement: P0 conformance gate SHALL be a required quality checkpoint
The project SHALL define a `p0-gate` conformance checkpoint that validates P0 runtime invariants before merge to protected branches.

- The gate MUST cover security policy gating, step-driven execution correctness, and event-log chain integrity.
- The gate MUST be configured as a required CI check for protected branch merges.

#### Scenario: Merge is blocked when p0-gate fails
- **GIVEN** a pull request targeting a protected branch
- **WHEN** `p0-gate` job fails
- **THEN** merge is blocked until the gate passes

### Requirement: P0 gate failures MUST be classified deterministically
The conformance gate SHALL classify failures into deterministic categories to accelerate triage.

- Failure categories MUST include: `SECURITY_REGRESSION`, `STEP_EXEC_REGRESSION`, and `AUDIT_CHAIN_REGRESSION`.
- CI output MUST include failing test identifiers and category labels.

#### Scenario: Security regression is labeled in CI output
- **WHEN** a security gating invariant test fails
- **THEN** CI summary marks the failure as `SECURITY_REGRESSION`

