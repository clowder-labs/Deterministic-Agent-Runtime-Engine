## ADDED Requirements

### Requirement: Runtime MUST support explicit execution mode selection
The runtime SHALL support explicit execution modes: `model_driven` and `step_driven`.

- `model_driven` MUST preserve existing model-selected tool invocation behavior.
- `step_driven` MUST execute only from validated plan steps.

#### Scenario: Default mode remains model-driven
- **WHEN** execution mode is not explicitly configured
- **THEN** the runtime uses `model_driven`
- **AND** existing tool-call behavior remains compatible

#### Scenario: Configured step-driven mode activates step executor path
- **WHEN** execution mode is set to `step_driven`
- **THEN** execute loop runs via the step executor path

### Requirement: Step-driven mode MUST execute steps deterministically
In `step_driven` mode the runtime SHALL execute `ValidatedPlan.steps` sequentially and deterministically.

- Each step MUST run in declared order.
- Previous successful step output MUST be available as step context for subsequent steps.
- Step failure MUST halt remaining steps unless a future policy explicitly enables continuation.

#### Scenario: Sequential step execution
- **GIVEN** three validated steps in a plan
- **WHEN** execute loop runs in `step_driven` mode
- **THEN** step 1, step 2, and step 3 are executed in order

#### Scenario: Step failure halts downstream steps
- **GIVEN** three validated steps in `step_driven` mode
- **WHEN** step 2 fails
- **THEN** step 3 is not executed
- **AND** execution returns failure with step-level errors

