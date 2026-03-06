## ADDED Requirements

### Requirement: Anthropic adapter uses direct model-name pass-through
The model domain SHALL provide an Anthropic adapter that can be selected via `Config.llm.adapter="anthropic"` and MUST accept model names as direct pass-through values from `Config.llm.model` or `ANTHROPIC_MODEL`.

#### Scenario: Adapter uses explicit model from config
- **WHEN** config provides model `claude-sonnet-4-5`
- **THEN** the adapter request uses `claude-sonnet-4-5` as-is

#### Scenario: Adapter requires model source when unset
- **WHEN** both `Config.llm.model` and `ANTHROPIC_MODEL` are missing
- **THEN** adapter initialization fails with an explicit model-required error

### Requirement: Anthropic adapter serializes tool history using Messages API blocks
The Anthropic adapter SHALL serialize assistant tool-call history and tool results according to Anthropic Messages API content blocks.

#### Scenario: Assistant history contains tool calls
- **WHEN** assistant history metadata includes tool calls
- **THEN** the adapter emits `tool_use` blocks with stable ids, names, and JSON object inputs

#### Scenario: Tool result is appended to history
- **WHEN** a tool result message is present in history
- **THEN** the adapter emits a user `tool_result` block that references the originating `tool_use_id`

### Requirement: Anthropic adapter normalizes response content and usage
The Anthropic adapter SHALL normalize response text, tool calls, thinking content, and usage fields into `ModelResponse`.

#### Scenario: Response includes text and tool_use blocks
- **WHEN** Anthropic response content contains `text` and `tool_use` blocks
- **THEN** `ModelResponse.content` contains the text content
- **AND** `ModelResponse.tool_calls` contains normalized tool calls

#### Scenario: Response includes usage counters
- **WHEN** Anthropic response usage provides input/output token counters
- **THEN** `ModelResponse.usage` includes `prompt_tokens`, `completion_tokens`, and `total_tokens`
