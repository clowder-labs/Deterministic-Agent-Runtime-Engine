## ADDED Requirements

### Requirement: Step-driven Execute Loop consumes validated steps

When runtime execution mode is `step_driven`, the system SHALL execute `ValidatedPlan.steps` sequentially through `IStepExecutor` instead of invoking the model-driven execute loop.

#### Scenario: Step-driven execution runs validated steps in order

- **GIVEN** a `ValidatedPlan` with ordered steps
- **AND** a configured `IStepExecutor`
- **WHEN** `DareAgent` runs execute loop in `step_driven` mode
- **THEN** each step is executed in sequence via `IStepExecutor.execute_step(...)`
- **AND** the returned step outputs are included in execute result outputs

#### Scenario: Missing plan fails fast in step-driven mode

- **GIVEN** `execution_mode` is `step_driven`
- **WHEN** execute loop is called without a validated plan
- **THEN** the runtime returns failure
- **AND** the error clearly indicates step-driven mode requires a validated plan

#### Scenario: Empty validated steps fail fast in step-driven mode

- **GIVEN** `execution_mode` is `step_driven`
- **AND** a validated plan with no steps
- **WHEN** execute loop starts
- **THEN** the runtime returns failure
- **AND** the error clearly indicates validated steps are required
