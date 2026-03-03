## ADDED Requirements

### Requirement: P0 conformance gate SHALL be a required quality checkpoint
The project SHALL define a `p0-gate` conformance checkpoint that validates P0 runtime invariants before merge to protected branches.

- The gate MUST cover security policy gating, step-driven execution correctness, and event-log chain integrity.
- The gate scope MUST define a stable category matrix mapping each invariant class to explicit test anchors and responsibility modules.
- Promotion of `p0-gate` to a required protected-branch check MUST require all selected category anchors to pass in a single run.
- The gate MUST be configured as a required CI check for protected branch merges.

#### Scenario: Merge is blocked when p0-gate fails
- **GIVEN** a pull request targeting a protected branch
- **WHEN** `p0-gate` job fails
- **THEN** merge is blocked until the gate passes

#### Scenario: Required-mode threshold demands all category anchors pass
- **GIVEN** the project is promoting `p0-gate` to a required branch check
- **WHEN** any selected security, step-driven, or audit anchor test fails
- **THEN** the gate remains non-promotable
- **AND** the rollout does not treat partial category success as sufficient

### Requirement: P0 gate failures MUST be classified deterministically
The conformance gate SHALL classify failures into deterministic categories to accelerate triage.

- Failure categories MUST include: `SECURITY_REGRESSION`, `STEP_EXEC_REGRESSION`, and `AUDIT_CHAIN_REGRESSION`.
- CI output MUST include failing test identifiers, category labels, and the primary modules responsible for the failing category.

#### Scenario: Security regression is labeled in CI output
- **WHEN** a security gating invariant test fails
- **THEN** CI summary marks the failure as `SECURITY_REGRESSION`

#### Scenario: CI summary includes module ownership for audit failure
- **WHEN** an event-log hash-chain or replay invariant fails
- **THEN** CI summary marks the failure as `AUDIT_CHAIN_REGRESSION`
- **AND** the summary identifies the primary audit-chain modules to inspect first
