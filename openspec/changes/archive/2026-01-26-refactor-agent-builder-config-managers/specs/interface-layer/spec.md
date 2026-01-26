## MODIFIED Requirements

### Requirement: AgentBuilder Composition API
The developer-facing agent API SHALL support composing agents via typed builders and deterministic resolution rules:

- The system SHALL provide builder variants for at least:
  - `SimpleChatAgent` (simple chat mode)
  - `FiveLayerAgent` (five-layer orchestration mode)
- Builders SHALL accept explicit component overrides (developer-injected instances) and SHALL treat them as highest precedence.
- When a required component is not explicitly provided, builders SHALL attempt to resolve it via the corresponding domain manager using the effective `Config`.
- For multi-load component categories (e.g., tools/hooks/validators), builders SHALL merge explicit components with manager-loaded components (extend semantics) while preserving injection order.
- Config enable/disable filtering MUST apply only to the manager-loaded subset and MUST NOT remove explicitly injected components.

#### Scenario: Resolve model adapter via manager
- **GIVEN** a builder with no explicit model adapter
- **AND** a provided `IModelAdapterManager`
- **AND** an effective `Config`
- **WHEN** `build()` is called
- **THEN** the builder MUST call `IModelAdapterManager.load_model_adapter(config=Config)` and use the returned adapter as the agent model

#### Scenario: Explicit model overrides manager
- **GIVEN** a builder with an explicitly injected model adapter via builder API
- **AND** a provided `IModelAdapterManager` that would otherwise return a different adapter
- **WHEN** `build()` is called
- **THEN** the explicitly injected adapter MUST be used

#### Scenario: Multi-load extend with config boundary
- **GIVEN** a builder with an explicitly injected tool `tool_x`
- **AND** a provided `IToolManager` that loads `tool_y` and `tool_z`
- **AND** config disables `tool_z`
- **WHEN** `build()` is called
- **THEN** `tool_x` and `tool_y` MUST be included and `tool_z` MUST be omitted, and `tool_x` MUST NOT be filtered out by config

## ADDED Requirements

### Requirement: Builder facade for variant selection
The system SHALL provide a stable facade for selecting which builder variant to use, such as:

- `Builder.simple_chat_agent_builder(name)` → builder for `SimpleChatAgent`
- `Builder.five_layer_agent_builder(name)` → builder for `FiveLayerAgent`

#### Scenario: Developer selects a builder variant
- **WHEN** a developer selects a builder variant via the facade
- **THEN** they receive a builder whose `build()` produces the corresponding agent type

