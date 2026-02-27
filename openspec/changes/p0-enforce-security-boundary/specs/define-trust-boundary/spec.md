## MODIFIED Requirements

### Requirement: Security Boundary Minimal Contract
The `ISecurityBoundary` interface SHALL expose a minimal contract that includes:
- verifying trusted input (`verify_trust`)
- checking policy decisions (`check_policy`)
- executing actions safely (`execute_safe`)

The runtime MUST treat these methods as mandatory preflight boundaries for side-effecting invocations, not optional helper hooks.

#### Scenario: Checking policy
- **WHEN** a tool action is evaluated
- **THEN** `check_policy` returns a decision such as `ALLOW`, `APPROVE_REQUIRED`, or `DENY`
- **AND** the runtime maps that decision to deterministic control flow

### Requirement: Security Boundary Positioning
The agent flow SHALL apply `ISecurityBoundary` checks before invoking tool execution or protocol adapters.

- `verify_trust` MUST run before policy evaluation.
- `check_policy` MUST run before `IToolGateway.invoke(...)`.
- A denied or unresolved decision MUST prevent downstream invocation.

#### Scenario: Enforcing ordering
- **WHEN** an agent prepares to invoke a tool
- **THEN** it verifies trust and policy before calling the tool gateway

#### Scenario: Denied policy prevents side effects
- **WHEN** `check_policy` returns `DENY`
- **THEN** the runtime terminates the invocation path
- **AND** no tool or protocol adapter is invoked

