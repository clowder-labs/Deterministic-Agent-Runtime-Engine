## RENAMED Requirements
- FROM: `### Requirement: Trust Boundary Interface`
- TO: `### Requirement: Security Boundary Interface`
- FROM: `### Requirement: Trust Boundary Minimal Contract`
- TO: `### Requirement: Security Boundary Minimal Contract`
- FROM: `### Requirement: Trust Boundary Positioning`
- TO: `### Requirement: Security Boundary Positioning`

## MODIFIED Requirements
### Requirement: Security Boundary Interface
The framework SHALL define an `ISecurityBoundary` interface that derives trusted inputs, enforces policy decisions, and executes actions within a sandbox boundary.

#### Scenario: Deriving trusted input
- **WHEN** a proposed tool input is supplied by the model
- **THEN** `ISecurityBoundary.verify_trust` returns a `TrustedInput` with derived risk and metadata.

### Requirement: Security Boundary Minimal Contract
The `ISecurityBoundary` interface SHALL expose a minimal contract that includes:
- verifying trusted input (`verify_trust`)
- checking policy decisions (`check_policy`)
- executing actions safely (`execute_safe`)

#### Scenario: Checking policy
- **WHEN** a tool action is evaluated
- **THEN** `check_policy` returns a decision such as ALLOW or APPROVE_REQUIRED.

### Requirement: Security Boundary Positioning
The agent flow SHALL apply `ISecurityBoundary` checks before invoking tool execution or protocol adapters.

#### Scenario: Enforcing ordering
- **WHEN** an agent prepares to invoke a tool
- **THEN** it verifies trust and policy before calling the tool gateway.
