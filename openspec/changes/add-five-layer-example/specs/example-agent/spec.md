# example-agent Specification Delta

## ADDED Requirements

### Requirement: Five-Layer Coding Agent Example
The repository SHALL include a `five-layer-coding-agent` example that demonstrates the complete five-layer loop architecture (Session → Milestone → Plan → Execute → Tool) using `FiveLayerAgent`.

#### Scenario: Five-layer example directory exists
- **GIVEN** the repository
- **WHEN** examining `examples/five-layer-coding-agent/`
- **THEN** the directory SHALL contain agent implementation, tools, planners, validators, tests, and documentation

#### Scenario: Example demonstrates full five-layer loop
- **WHEN** the five-layer coding agent runs a task
- **THEN** it SHALL execute through Session Loop, Milestone Loop, Plan Loop, Execute Loop, and Tool Loop as designed in the architecture

#### Scenario: Example provides both deterministic and real model modes
- **GIVEN** the five-layer coding agent example
- **WHEN** configured in deterministic mode
- **THEN** it SHALL run without external API calls using a `DeterministicPlanner`
- **AND WHEN** configured in OpenAI mode
- **THEN** it SHALL use `OpenAIPlanner` to generate plans via real model calls

### Requirement: Five-Layer Example Tool Set
The five-layer coding agent example SHALL include a representative set of tools covering different risk levels and operation types.

#### Scenario: Read-only tools
- **GIVEN** the five-layer coding agent
- **WHEN** examining registered tools
- **THEN** it SHALL include `read_file` and `search_code` tools (READ_ONLY risk level)

#### Scenario: Write tools
- **GIVEN** the five-layer coding agent
- **WHEN** examining registered tools
- **THEN** it SHALL include `write_file` and `edit_file` tools (IDEMPOTENT_WRITE risk level)

#### Scenario: Execute tools
- **GIVEN** the five-layer coding agent
- **WHEN** examining registered tools
- **THEN** it SHALL include `run_tests` tool (NON_IDEMPOTENT_EFFECT risk level)

### Requirement: Five-Layer Example Planner Implementations
The five-layer coding agent example SHALL provide both deterministic and AI-driven planner implementations.

#### Scenario: Deterministic planner for testing
- **GIVEN** `planners/deterministic.py`
- **WHEN** instantiated with a predefined plan
- **THEN** it SHALL return that plan without model calls
- **AND** SHALL be suitable for unit tests and CI environments

#### Scenario: OpenAI planner for demonstration
- **GIVEN** `planners/openai_planner.py`
- **WHEN** called with a task and context
- **THEN** it SHALL use `IModelAdapter` to generate a `ProposedPlan`
- **AND** SHALL parse model output into plan steps

### Requirement: Five-Layer Example Validator
The five-layer coding agent example SHALL include a validator that verifies plans and milestone completion.

#### Scenario: Plan validation
- **GIVEN** `validators/simple_validator.py`
- **WHEN** `validate_plan` is called with a `ProposedPlan`
- **THEN** it SHALL check tool existence, parameter completeness, and circular dependencies
- **AND** SHALL return a `ValidatedPlan` or raise validation errors

#### Scenario: Milestone verification
- **GIVEN** `validators/simple_validator.py`
- **WHEN** `verify_milestone` is called with an `ExecuteResult`
- **THEN** it SHALL check for execution errors and expected outputs
- **AND** SHALL return a `VerifyResult` with success status and collected evidence

### Requirement: Five-Layer Example Integration Tests
The five-layer coding agent example SHALL include integration tests that verify end-to-end execution in deterministic mode.

#### Scenario: Single milestone task completion
- **GIVEN** a simple task with one milestone
- **WHEN** the deterministic agent executes the task
- **THEN** it SHALL complete successfully through all five loops
- **AND** SHALL produce expected tool outputs

#### Scenario: Multi-milestone task completion
- **GIVEN** a complex task with multiple milestones
- **WHEN** the deterministic agent executes the task
- **THEN** it SHALL complete each milestone sequentially
- **AND** SHALL track progress through all milestones

#### Scenario: Plan validation failure retry
- **GIVEN** a planner that initially produces an invalid plan
- **WHEN** the plan loop executes
- **THEN** it SHALL retry plan generation up to max_plan_attempts
- **AND** SHALL eventually succeed or fail gracefully

### Requirement: Five-Layer Example Documentation
The five-layer coding agent example SHALL include comprehensive documentation.

#### Scenario: README covers architecture
- **GIVEN** `examples/five-layer-coding-agent/README.md`
- **WHEN** a developer reads it
- **THEN** it SHALL explain the five-layer loop architecture
- **AND** SHALL include a diagram or description of each loop

#### Scenario: README provides usage instructions
- **GIVEN** `examples/five-layer-coding-agent/README.md`
- **WHEN** a developer reads it
- **THEN** it SHALL explain how to run deterministic mode
- **AND** SHALL explain how to configure OpenAI mode with environment variables
- **AND** SHALL list example task scenarios

#### Scenario: README documents limitations
- **GIVEN** `examples/five-layer-coding-agent/README.md`
- **WHEN** a developer reads it
- **THEN** it SHALL document known limitations (e.g., mocked components)
- **AND** SHALL reference design gap tracking if applicable

## MODIFIED Requirements

None - This change only adds new requirements to the example-agent capability.

## REMOVED Requirements

None - This change preserves all existing example-agent requirements.
