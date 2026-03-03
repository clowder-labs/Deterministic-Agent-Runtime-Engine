## MODIFIED Requirements

### Requirement: React plan hint injection MUST reflect canonical plan state
When a `plan_provider` is mounted on `ReactAgent`, injected `critical_block` MUST be derived from canonical plan/step lifecycle state, not only from completed id sets.

The hint MUST include:
- current `plan_status`
- pending/completed step view
- deterministic NEXT action guidance (`validate_plan`, `sub_agent_*`, or `finish_plan`)

#### Scenario: prompt asks to finish when all steps are done
- **GIVEN** all steps are in `done` and plan state is not terminal
- **WHEN** `critical_block` is generated
- **THEN** NEXT guidance asks to call `finish_plan(target_state="done")`

#### Scenario: prompt asks to validate before execution
- **GIVEN** plan exists but is not validated
- **WHEN** `critical_block` is generated
- **THEN** NEXT guidance asks to call `validate_plan(success=True)`

