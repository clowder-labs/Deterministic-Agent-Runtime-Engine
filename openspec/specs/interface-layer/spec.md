# interface-layer Specification

## Purpose
TBD - created by archiving the prior plugin-system change. Update Purpose after archive.
## Requirements
### Requirement: Shared types are canonical
The system SHALL locate canonical types within their owning domains (context, tool, plan, event, hook, security, model, memory, config) and SHALL use them across Kernel/components/examples.

#### Scenario: Tool loop returns canonical ToolResult
- **GIVEN** a tool invocation through the Tool Loop
- **WHEN** it completes
- **THEN** the result is represented using the canonical `ToolResult` type.

### Requirement: Core Interface Coverage
The interface layer SHALL define Kernel and Component contracts, including a shared component identity contract (`IComponent`) and the shared `ComponentType` enum.

#### Scenario: Developer imports shared component identity
- **WHEN** a developer implements a pluggable component
- **THEN** they can implement `IComponent` and reference `ComponentType` from the canonical infra module

### Requirement: Core Data Models
The interface layer SHALL provide canonical data models, including:
`CapabilityDescriptor`, `CapabilityType`, `Envelope`, `Budget`, `ToolDefinition`, `ToolResult`, `ExecutionSignal`, `Checkpoint`, `Task`, `Milestone`, `RunResult`, `Event`, `RuntimeSnapshot`, `HookPhase`, `RiskLevel`, `PolicyDecision`, `TrustedInput`, and `SandboxSpec`.

#### Scenario: Kernel and providers exchange canonical models
- **WHEN** a capability is discovered and invoked through the gateway
- **THEN** capability descriptors and envelopes use the canonical models (no protocol-specific leakage).

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

### Requirement: Optional MCP Integration Surface
The interface layer SHALL define IMCPClient and MCPToolkit, and MCP integration SHALL keep the default runtime functional when no MCP clients are configured.

#### Scenario: MCP is not configured
- **WHEN** no MCP clients are provided
- **THEN** the runtime operates with local tools only and does not attempt MCP discovery

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

### Requirement: Manager interfaces are domain-owned
The system SHALL define component manager interfaces alongside their owning domain interfaces, not in the config domain. Specifically:
- Tool manager: `dare_framework/tool/interfaces.py`
- Model adapter manager: `dare_framework/model/interfaces.py`
- Planner/validator/remediator managers: `dare_framework/plan/interfaces.py`
- Hook manager: `dare_framework/hook/interfaces.py`

The protocol adapter manager SHALL be defined at the package root in `dare_framework/protocol_adapter_manager.py` until a dedicated protocol domain exists.

#### Scenario: Tool manager import path
- **WHEN** a contributor imports `IToolManager`
- **THEN** it is available from `dare_framework.tool.interfaces` and not from `dare_framework.config.interfaces`.

#### Scenario: Plan manager grouping
- **WHEN** a contributor looks for planner/validator/remediator managers
- **THEN** the manager interfaces are defined alongside `IPlanner`, `IValidator`, and `IRemediator` in the plan domain.

#### Scenario: Protocol adapter manager root
- **WHEN** a contributor imports `IProtocolAdapterManager`
- **THEN** it is available from `dare_framework.protocol_adapter_manager`.

### Requirement: Tool manager contract
The interface layer SHALL define an `IToolManager` contract in the tool domain. The contract SHALL support trusted tool registration, provider aggregation, and prompt tool definition export without executing tools. At minimum it MUST include:
- `register_tool(...)`, `unregister_tool(...)`, `update_tool(...)`
- `register_provider(...)`, `unregister_provider(...)`
- `list_capabilities(...)`, `refresh(...)`
- `list_tool_defs(...)`, `get_capability(...)`
- `health_check(...)`

#### Scenario: Register tool returns a capability descriptor
- **GIVEN** a valid `ITool` implementation
- **WHEN** `register_tool(...)` is called
- **THEN** the manager returns a `CapabilityDescriptor` with a stable `capability_id` and trusted metadata

#### Scenario: Tool definitions are derived from registry
- **GIVEN** a tool has been registered into the manager
- **WHEN** `list_tool_defs()` is called
- **THEN** the result is derived from the manager registry and not from model output

### Requirement: Builder facade for variant selection
The system SHALL provide a stable facade for selecting which builder variant to use, such as:

- `Builder.simple_chat_agent_builder(name)` → builder for `SimpleChatAgent`
- `Builder.five_layer_agent_builder(name)` → builder for `FiveLayerAgent`

#### Scenario: Developer selects a builder variant
- **WHEN** a developer selects a builder variant via the facade
- **THEN** they receive a builder whose `build()` produces the corresponding agent type

