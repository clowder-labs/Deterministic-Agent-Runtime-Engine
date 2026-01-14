## ADDED Requirements
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
