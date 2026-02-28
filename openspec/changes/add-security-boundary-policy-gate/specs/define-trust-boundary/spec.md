## ADDED Requirements

### Requirement: Canonical default security boundary implementation

The security domain SHALL provide a default concrete `ISecurityBoundary` implementation for canonical runtime usage.

#### Scenario: Default boundary derives trusted input

- **WHEN** `verify_trust` is called with untrusted params and context
- **THEN** it returns a `TrustedInput` with normalized params and a valid `RiskLevel`

#### Scenario: Default boundary policy is permissive

- **WHEN** `check_policy` is called with any action/resource/context
- **THEN** it returns `PolicyDecision.ALLOW` by default

#### Scenario: Default boundary executes async call safely

- **WHEN** `execute_safe` wraps an async callable
- **THEN** it awaits the callable and returns the underlying result
