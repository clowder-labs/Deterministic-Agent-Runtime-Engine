## ADDED Requirements
### Requirement: Runtime dispatches hook events
The runtime SHALL dispatch each logged event to all configured hooks in emission order.

#### Scenario: Event emitted during a run
- **WHEN** the runtime logs an event such as `plan.attempt` or `tool.invoke`
- **THEN** each configured hook receives an `Event` with the same `event_type` and payload

### Requirement: Hook errors are non-fatal
Hook execution failures SHALL NOT stop or fail the runtime.

#### Scenario: Hook raises an exception
- **WHEN** a hook raises an exception while handling an event
- **THEN** the runtime continues execution and records the hook failure as a runtime event

### Requirement: Hook-visible plan, model, and tool details
The runtime SHALL emit hook-visible events that include plan details, model responses, and tool results.

#### Scenario: Plan proposed and validated
- **WHEN** a plan is proposed and validated
- **THEN** an event includes the plan description and step details (tool name, description, inputs)

#### Scenario: Model returns a response
- **WHEN** the model returns a response with or without tool calls
- **THEN** an event includes the assistant content and any tool call metadata

#### Scenario: Tool execution completes
- **WHEN** a tool finishes executing
- **THEN** an event includes the tool name, success flag, output, and error (if any)

### Requirement: Stdout hook for human-readable tracing
The system SHALL provide a hook implementation that writes human-readable, line-oriented summaries of runtime events to stdout.

#### Scenario: Hook receives a tool invocation
- **WHEN** the stdout hook receives a `tool.invoke` event
- **THEN** it prints a tagged line containing the tool name and arguments

#### Scenario: Hook receives a model response
- **WHEN** the stdout hook receives a model response event
- **THEN** it prints a tagged line containing the assistant content and a summary of tool calls
