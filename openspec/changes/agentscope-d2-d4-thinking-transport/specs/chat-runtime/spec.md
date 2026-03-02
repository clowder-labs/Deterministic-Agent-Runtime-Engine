## MODIFIED Requirements

### Requirement: LLM-driven execute loop
The runtime SHALL invoke the configured `IModelAdapter` during the execute loop, provide the assembled prompt and available tool definitions, and iterate over tool calls until the model returns a final response.

The execute loop SHALL preserve adapter-extracted `thinking_content` and normalized `reasoning_tokens` in the model response payload used by runtime hooks/transport emission.

When runtime transport emission is enabled, the execute loop SHALL emit canonical intermediate events (`thinking`, `tool_call`, `tool_result`) in execution order prior to final `message` output.

#### Scenario: Model returns a final response
- **WHEN** the model response contains no tool calls
- **THEN** the execute loop returns success and exposes the response content in the run output

#### Scenario: Model requests a tool call
- **WHEN** the model response includes a tool call
- **THEN** the runtime executes the tool via `ToolRuntime`, appends the result to the message history, and continues

#### Scenario: Runtime preserves reasoning content and tokens
- **WHEN** adapter response includes thinking content and reasoning token usage
- **THEN** runtime keeps `thinking_content` in the model response object
- **AND** usage contains normalized `reasoning_tokens`

#### Scenario: Runtime emits ordered intermediate events
- **GIVEN** transport sender is configured
- **WHEN** the runtime performs one round with model thinking and one tool call
- **THEN** emitted events preserve order `thinking -> tool_call -> tool_result -> message`
