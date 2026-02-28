# chat-runtime Specification

## Purpose
TBD - created by archiving change add-basic-chat-flow. Update Purpose after archive.
## Requirements
### Requirement: LLM-driven execute loop
The runtime SHALL invoke the configured `IModelAdapter` during the execute loop, provide the assembled prompt and available tool definitions, and iterate over tool calls until the model returns a final response.

#### Scenario: Model returns a final response
- **WHEN** the model response contains no tool calls
- **THEN** the execute loop returns success and exposes the response content in the run output

#### Scenario: Model requests a tool call
- **WHEN** the model response includes a tool call
- **THEN** the runtime executes the tool via `ToolRuntime`, appends the result to the message history, and continues

### Requirement: Interactive stdin/stdout chat example
The system SHALL provide a stdin/stdout example that wires the OpenAI adapter, base prompt store, and local command tool into an agent to perform interactive dialogue.

#### Scenario: User provides a prompt
- **WHEN** a user types a non-empty line into stdin
- **THEN** the example invokes the agent and prints the model response to stdout

#### Scenario: User quits the session
- **WHEN** a user enters `/quit`
- **THEN** the example exits without invoking the agent

#### Scenario: Session context preserved across turns
- **WHEN** a user sends multiple prompts in one session
- **THEN** the example includes the prior turn context in subsequent model requests

### Requirement: Example wires LLM placeholders and stdout hook
The example SHALL include placeholder LLM configuration in code and enable the stdout hook to surface plan/model/tool activity.

#### Scenario: Developer fills in LLM settings
- **WHEN** the developer updates the placeholder model configuration
- **THEN** the example uses those settings for LLM calls and prints hook output to stdout

### Requirement: Default context assembly fuses STM/LTM/Knowledge
The canonical default `Context.assemble()` path SHALL include retrieval results from LTM and Knowledge in addition to STM when sources are available.

#### Scenario: Assemble includes all available sources
- **GIVEN** STM has recent messages and both LTM and Knowledge are configured
- **WHEN** `Context.assemble()` is called
- **THEN** assembled messages include STM messages plus retrieved LTM and Knowledge messages
- **AND** retrieval metadata includes source counts and query text

### Requirement: Retrieval query derives from current user intent
The default assembly strategy SHALL derive retrieval query from the latest user-intent message in STM.

#### Scenario: Latest user message drives retrieval query
- **GIVEN** STM contains multiple turns including at least one user message
- **WHEN** `Context.assemble()` is called
- **THEN** LTM and Knowledge retrieval are invoked with the latest user message content as query

### Requirement: Budget-aware degradation for retrieval sources
The default assembly strategy SHALL degrade retrieval under low remaining token budget before model invocation.

#### Scenario: Low budget skips retrieval sources
- **GIVEN** remaining token budget is insufficient after reserving baseline STM and safety buffer
- **WHEN** `Context.assemble()` is called
- **THEN** LTM/Knowledge retrieval results are omitted
- **AND** metadata marks `degraded=true` with degradation reason

#### Scenario: Retrieval exceptions degrade source without failing assemble
- **GIVEN** one retrieval source raises an exception during get
- **WHEN** `Context.assemble()` is called
- **THEN** assemble still succeeds with available sources
- **AND** metadata records degraded source reason
