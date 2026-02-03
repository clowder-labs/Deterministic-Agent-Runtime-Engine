## ADDED Requirements

### Requirement: Milestone 自动拆分能力（LLM Decomposition）

The system SHALL provide an `IPlanner.decompose(task, ctx)` method that decomposes a `Task` into a list of `Milestone` objects, enabling LLM-driven automatic task decomposition.

- `decompose` MUST return a `DecompositionResult` containing `milestones` list and `reasoning` string.
- If `Task.milestones` is already populated, decomposition SHOULD be skipped.
- A default implementation SHALL return a single milestone derived from `task.description`.

#### Scenario: LLM decomposes complex task

- **GIVEN** a Task with empty milestones and a configured LLM planner
- **WHEN** `IPlanner.decompose(task, ctx)` is called
- **THEN** the planner returns multiple Milestones with distinct descriptions and success_criteria

#### Scenario: Simple task uses single milestone

- **GIVEN** a Task with empty milestones and default planner
- **WHEN** `IPlanner.decompose(task, ctx)` is called
- **THEN** a single Milestone is returned with description matching task.description

#### Scenario: Pre-defined milestones skip decomposition

- **GIVEN** a Task with pre-defined milestones
- **WHEN** Session Loop initializes
- **THEN** `decompose` is NOT called and pre-defined milestones are used

---

### Requirement: 结构化证据收集与验证（Evidence Closure）

The system SHALL provide structured evidence collection and mandatory verification against milestone success criteria.

- `Evidence` dataclass MUST include: `evidence_id`, `evidence_type`, `source`, `data`, `timestamp`.
- `VerifyResult` MUST be extended with `evidence_required` and `evidence_collected` fields.
- `IValidator.verify_milestone` SHOULD check that collected evidence satisfies success_criteria.
- Tool results SHOULD automatically produce `Evidence` entries with `evidence_type="tool_result"`.

#### Scenario: Tool result produces evidence

- **GIVEN** a tool invocation via `IToolGateway.invoke()`
- **WHEN** the tool returns a result
- **THEN** an `Evidence` object is created with type "tool_result" and added to milestone state

#### Scenario: Milestone verification checks evidence

- **GIVEN** a Milestone with success_criteria ["file_created", "tests_pass"]
- **WHEN** `verify_milestone` is called with collected evidence
- **THEN** the validator checks evidence against criteria and returns success only if all criteria are satisfied

#### Scenario: Missing evidence causes verification failure

- **GIVEN** a Milestone with success_criteria ["api_response_200"]
- **WHEN** `verify_milestone` is called with no matching evidence
- **THEN** the validator returns `success=False` with error indicating missing evidence

---

### Requirement: DecompositionResult 类型定义

The plan module SHALL provide a `DecompositionResult` type to carry milestone decomposition output.

- `DecompositionResult` MUST contain: `milestones: list[Milestone]`, `reasoning: str`, `metadata: dict`.
- The type MUST be immutable (frozen dataclass).

#### Scenario: Access decomposition result

- **WHEN** a decomposition is performed
- **THEN** the result provides milestones list and reasoning string for auditability
