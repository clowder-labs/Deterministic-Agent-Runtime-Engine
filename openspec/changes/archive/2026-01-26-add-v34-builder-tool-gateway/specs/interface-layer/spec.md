## MODIFIED Requirements
### Requirement: AgentBuilder Composition API
The developer API (AgentBuilder or equivalent) SHALL be available in the canonical `dare_framework` package and SHALL support composing a v3.4 baseline agent with: context, model adapter, budget, and tool wiring (tool gateway + tool provider). Optional memory/knowledge inputs MAY be supplied for context assembly.

#### Scenario: Minimal v3.4 build and run
- **GIVEN** a minimal AgentBuilder with a deterministic in-process model adapter and no external tools
- **WHEN** the built agent executes a task
- **THEN** it completes without network access and returns the adapter output

#### Scenario: Tools are exposed through the gateway-backed tool provider
- **GIVEN** AgentBuilder registers local tools into the default tool gateway
- **WHEN** Context assembles tool definitions
- **THEN** the tool list is derived from `IToolGateway.list_capabilities()`

## ADDED Requirements
### Requirement: Default ToolGateway Aggregates Capability Providers
The canonical `dare_framework` package SHALL provide a default `IToolGateway` implementation that aggregates registered `ICapabilityProvider`s and enforces envelope allowlists during invocation.

#### Scenario: List capabilities from multiple providers
- **GIVEN** two registered capability providers
- **WHEN** `list_capabilities()` is called
- **THEN** it returns the combined capability descriptors without duplicate ids

#### Scenario: Reject disallowed capability invoke
- **GIVEN** an envelope with `allowed_capability_ids` that does not include a requested capability
- **WHEN** `invoke()` is called
- **THEN** the gateway rejects the request
