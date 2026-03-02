## ADDED Requirements

### Requirement: Canonical thinking and tool intermediate events
The runtime SHALL expose canonical intermediate event types for model/tool execution progress using the following event taxonomy: `message`, `tool_call`, `tool_result`, `thinking`, `error`, `status`.

#### Scenario: Runtime emits tool lifecycle events
- **WHEN** the model requests one or more tool calls
- **THEN** the runtime emits at least one `tool_call` event before tool execution
- **AND** emits a matching `tool_result` event after tool execution

#### Scenario: Runtime emits thinking event when available
- **WHEN** adapter extraction returns non-empty `thinking_content`
- **THEN** the runtime emits a `thinking` event before final `message` output

### Requirement: Model response preserves reasoning content and usage
`ModelResponse` SHALL preserve model reasoning content in `thinking_content` and SHALL normalize `reasoning_tokens` into usage metadata when provider payload includes reasoning token usage.

#### Scenario: Adapter extracts reasoning content
- **WHEN** provider payload includes a reasoning/thinking field
- **THEN** `ModelResponse.thinking_content` is populated with extracted text

#### Scenario: Adapter normalizes reasoning token usage
- **WHEN** provider payload includes reasoning token counters
- **THEN** `ModelResponse.usage["reasoning_tokens"]` is present and numeric

### Requirement: Legacy transport aliases remain consumable
Transport event type normalization SHALL continue to accept legacy aliases and map them to canonical values without breaking existing clients.

#### Scenario: Legacy approval alias is normalized
- **WHEN** an envelope arrives with a legacy approval alias event type
- **THEN** runtime normalization maps it to the canonical event type value before dispatch
