## MODIFIED Requirements

### Requirement: LLM-driven execute loop
The runtime SHALL invoke the configured `IModelAdapter` during the execute loop and iterate over tool calls until the model returns a final response.

Before each model invocation, the execute loop SHALL perform token-aware context compression when configured thresholds are exceeded.

#### Scenario: Execute loop auto-compresses before model call
- **GIVEN** a ReAct run with context token usage above configured threshold
- **WHEN** the loop prepares to call `model.generate`
- **THEN** context compression runs before model invocation
- **AND** resulting model call sees compressed context messages
