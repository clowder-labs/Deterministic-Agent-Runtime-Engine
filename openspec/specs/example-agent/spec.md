# example-agent Specification

## Purpose
TBD - created by archiving the prior plugin-system change. Update Purpose after archive.
## Requirements
### Requirement: Verification examples track canonical contracts
The canonical examples SHALL remain present and SHALL be updated to use the agent-domain builder API.

#### Scenario: Basic chat example imports agent builder
- **GIVEN** `examples/basic-chat/chat_simple.py`
- **WHEN** it is executed in a configured environment
- **THEN** it composes the agent using `BaseAgent` builder factories

### Requirement: Framework-Backed Coding Agent Example
The example agent SHALL be built using the developer API and SHALL register tools (directly or via tool-group providers) in a way that exercises the Kernel `IToolGateway` boundary.

#### Scenario: Example agent instantiation
- **WHEN** a developer instantiates the example agent
- **THEN** it composes Kernel defaults, a deterministic planner/model adapter, and a minimal tool set

### Requirement: Deterministic Mock Mode
The example agent SHALL support a deterministic mode that uses a MockModelAdapter and/or DeterministicPlanGenerator to avoid external LLM calls.

#### Scenario: Mocked run
- **WHEN** the agent runs in deterministic mode
- **THEN** it completes the workflow without network access and returns fixed outputs

### Requirement: Optional Real Model Adapter
The example agent SHALL allow configuration of a real IModelAdapter, and this path SHALL remain optional and non-default.

#### Scenario: Real model configured
- **WHEN** a user configures a real model adapter
- **THEN** the agent delegates plan/execute generation to that adapter

### Requirement: Example Flow Validation
The repository SHALL include an integration test (or equivalent validation) that runs the example end-to-end in deterministic/mock mode and asserts a successful RunResult, including event log evidence.

#### Scenario: Example flow test
- **WHEN** the example flow test is executed
- **THEN** it completes without network access and asserts success + key audit events

### Requirement: Environment Configuration Security
The five-layer coding agent example SHALL use environment variables for sensitive configuration and SHALL NOT commit API keys to the repository.

#### Scenario: Environment variable template
- **GIVEN** the five-layer coding agent example
- **WHEN** examining the directory
- **THEN** it SHALL include `.env.example` as a configuration template
- **AND** SHALL NOT include `.env` file in git repository
- **AND** `.gitignore` SHALL include `.env` and related patterns

#### Scenario: API key security
- **GIVEN** the example implementation
- **WHEN** examining source code
- **THEN** it SHALL load API keys from environment variables using `os.getenv()`
- **AND** SHALL NOT contain hardcoded API keys or tokens
- **AND** README SHALL warn users not to commit `.env` files

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
- **AND WHEN** configured in OpenRouter mode
- **THEN** it SHALL use `OpenRouterPlanner` to generate plans via real model calls

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

#### Scenario: OpenRouter planner for demonstration
- **GIVEN** `planners/openrouter_planner.py`
- **WHEN** called with a task and context
- **THEN** it SHALL use `IModelAdapter` to generate a `ProposedPlan`
- **AND** SHALL parse model output into plan steps
- **AND** SHALL use OpenRouter API (compatible with OpenAI SDK)

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
- **AND** SHALL explain how to configure OpenRouter mode with environment variables
- **AND** SHALL provide instructions for setting up `.env` file from `.env.example`
- **AND** SHALL list recommended free models (e.g., `xiaomi/mimo-v2-flash:free`)
- **AND** SHALL list example task scenarios

#### Scenario: README documents limitations
- **GIVEN** `examples/five-layer-coding-agent/README.md`
- **WHEN** a developer reads it
- **THEN** it SHALL document known limitations (e.g., mocked components)
- **AND** SHALL reference design gap tracking if applicable

