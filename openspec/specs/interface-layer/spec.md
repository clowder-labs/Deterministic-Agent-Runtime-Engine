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
The interface layer SHALL define Kernel and Component contracts, including:

- Kernel: `IContextManager`, `IResourceManager`, `IToolGateway`, `IExecutionControl`, `IEventLog`, `IExtensionPoint`, `IConfigProvider`, `ISecurityBoundary`
- Component: `IContextStrategy`, `IModelAdapter`, `IMemory`, `IPromptStore`, `ITool`, `ISkill`, `ICapabilityProvider`, `IProtocolAdapter`, `IMCPClient`, `IPlanner`, `IValidator`, `IRemediator`, `IEventListener`, `IHook`

#### Scenario: Developer implements a custom component
- **WHEN** a developer imports and implements any domain interface
- **THEN** the contract surface is available, typed, and usable for composition.

### Requirement: Core Data Models
The interface layer SHALL provide canonical data models, including:
`CapabilityDescriptor`, `CapabilityType`, `Envelope`, `Budget`, `ToolDefinition`, `ToolResult`, `ExecutionSignal`, `Checkpoint`, `Task`, `Milestone`, `RunResult`, `Event`, `RuntimeSnapshot`, `HookPhase`, `RiskLevel`, `PolicyDecision`, `TrustedInput`, and `SandboxSpec`.

#### Scenario: Kernel and providers exchange canonical models
- **WHEN** a capability is discovered and invoked through the gateway
- **THEN** capability descriptors and envelopes use the canonical models (no protocol-specific leakage).

### Requirement: AgentBuilder Composition API
The developer-facing agent API SHALL support direct composition of core components by passing optional overrides into agent constructors, with defaults created when omitted.

#### Scenario: Minimal build and run
- **WHEN** a developer constructs an agent with a model adapter and tools
- **THEN** the agent can execute a deterministic end-to-end flow without external builder scaffolding.

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

