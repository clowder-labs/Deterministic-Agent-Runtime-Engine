## ADDED Requirements
### Requirement: BaseAgent is a public agent entry point
The agent domain SHALL expose `BaseAgent` as a public type, and built-in agents SHALL inherit from it.

#### Scenario: Developer imports BaseAgent
- **WHEN** a developer imports `BaseAgent` from `dare_framework.agent`
- **THEN** the import succeeds without referencing `_internal` modules

## MODIFIED Requirements
### Requirement: Builder facade for variant selection
The system SHALL provide a stable facade for selecting which builder variant to use via `BaseAgent`, such as:

- `BaseAgent.simple_chat_agent_builder(name)` → builder for `SimpleChatAgent`
- `BaseAgent.five_layer_agent_builder(name)` → builder for `FiveLayerAgent`

#### Scenario: Developer selects a builder variant
- **WHEN** a developer selects a builder variant via `BaseAgent`
- **THEN** they receive a builder whose `build()` produces the corresponding agent type
