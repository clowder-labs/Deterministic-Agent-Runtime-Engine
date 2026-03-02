## ADDED Requirements

### Requirement: plan_v2 Step/Plan MUST use explicit lifecycle states
`plan_v2` SHALL expose explicit lifecycle states for both step and plan using `todo`, `in_progress`, `done`, `abandoned`.

`step` and `plan` state transitions MUST follow defined legal transitions, and illegal transitions MUST be rejected with deterministic errors.

#### Scenario: valid step transition
- **GIVEN** a step in `todo`
- **WHEN** runtime transitions it to `in_progress` then `done`
- **THEN** both transitions succeed
- **AND** the step final state is `done`

#### Scenario: invalid terminal transition
- **GIVEN** a step in `done`
- **WHEN** runtime tries to transition it back to `in_progress`
- **THEN** transition is rejected
- **AND** a deterministic error is returned

### Requirement: plan_v2 MUST support runtime plan revision and explicit finish
`plan_v2` SHALL provide tools `revise_current_plan` and `finish_plan`.

- `revise_current_plan` MUST allow modifying current plan while preserving valid completed progress by `step_id`.
- `finish_plan(target_state="done")` MUST fail if non-terminal steps remain.
- `finish_plan(target_state="abandoned")` MUST mark remaining non-terminal steps as `abandoned`.

#### Scenario: revise existing plan
- **GIVEN** an existing validated plan in progress
- **WHEN** `revise_current_plan` is called with updated steps
- **THEN** plan description and steps are updated
- **AND** completed step progress remains consistent where step_id matches

#### Scenario: reject premature done
- **GIVEN** a plan with pending steps
- **WHEN** `finish_plan(target_state="done")` is called
- **THEN** tool returns failure
- **AND** plan state does not move to `done`

