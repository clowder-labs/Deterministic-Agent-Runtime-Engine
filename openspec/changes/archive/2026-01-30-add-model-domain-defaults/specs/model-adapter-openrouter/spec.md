## ADDED Requirements
### Requirement: OpenRouter model adapter
The system SHALL provide an `IModelAdapter` implementation for OpenRouter (OpenAI-compatible API) under the model domain, configurable via `Config.llm` fields or explicit constructor parameters.

#### Scenario: Generate a response via OpenRouter
- **WHEN** `generate(...)` is called with `ModelInput`
- **THEN** the adapter returns a `ModelResponse` with content and normalized tool calls
