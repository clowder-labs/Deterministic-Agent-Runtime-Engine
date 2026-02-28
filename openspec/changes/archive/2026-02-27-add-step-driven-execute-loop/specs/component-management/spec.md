## ADDED Requirements

### Requirement: DareAgentBuilder exposes execution-mode wiring

`DareAgentBuilder` SHALL expose explicit builder APIs for execution strategy wiring so callers can deterministically select runtime behavior.

#### Scenario: Builder sets execution mode explicitly

- **GIVEN** a `DareAgentBuilder`
- **WHEN** caller configures `with_execution_mode("step_driven")`
- **THEN** built `DareAgent` runs with `execution_mode="step_driven"`

#### Scenario: Builder injects custom step executor

- **GIVEN** a custom `IStepExecutor` implementation
- **WHEN** caller configures `with_step_executor(custom_executor)`
- **THEN** built `DareAgent` uses that executor in step-driven mode

#### Scenario: Builder default remains model-driven

- **GIVEN** a `DareAgentBuilder` with no execution-mode customization
- **WHEN** the agent is built
- **THEN** `execution_mode` remains `model_driven`
- **AND** existing model-driven runtime behavior is unchanged
