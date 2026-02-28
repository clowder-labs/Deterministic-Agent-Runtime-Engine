## ADDED Requirements

### Requirement: Plan execution policy gate in DareAgent

`DareAgent` SHALL apply security policy check before entering Execute Loop from Milestone Loop.

#### Scenario: Plan execution denied by policy

- **GIVEN** a configured security boundary
- **AND** `check_policy(action="execute_plan", ...)` returns `DENY`
- **WHEN** milestone execution reaches plan->execute boundary
- **THEN** Execute Loop is not entered
- **AND** the milestone fails with an explicit security policy error

#### Scenario: Plan execution requires approval without bridge

- **GIVEN** a configured security boundary
- **AND** `check_policy(action="execute_plan", ...)` returns `APPROVE_REQUIRED`
- **WHEN** milestone execution reaches plan->execute boundary
- **THEN** Execute Loop is not entered
- **AND** the milestone fails with an explicit security approval error

### Requirement: Tool invocation boundary enforces trust and policy

`DareAgent` Tool Loop SHALL derive trusted params and enforce policy before invoking tool gateway.

#### Scenario: Tool invocation denied by policy

- **GIVEN** `check_policy(action="invoke_tool", ...)` returns `DENY`
- **WHEN** Tool Loop attempts invocation
- **THEN** tool gateway is not invoked
- **AND** Tool Loop returns failure with a security policy error

#### Scenario: Tool invocation uses trusted params

- **GIVEN** `verify_trust` returns transformed trusted params
- **AND** policy decision is `ALLOW`
- **WHEN** Tool Loop invokes the capability
- **THEN** tool gateway receives the trusted params instead of raw params

#### Scenario: Tool invocation wrapped by execute_safe

- **GIVEN** policy decision is `ALLOW`
- **WHEN** Tool Loop invokes a tool
- **THEN** invocation is executed via `ISecurityBoundary.execute_safe(...)`
