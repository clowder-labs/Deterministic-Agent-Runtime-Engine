# interface-layer Specification

## Purpose
TBD - created by archiving change refactor-plugin-system-v2. Update Purpose after archive.
## Requirements
### Requirement: Shared types are v2-aligned
The system SHALL locate shared canonical types (evidence, risk levels, tool results/definitions, model message types) in v2-aligned modules and SHALL use them across Kernel/components/examples.

#### Scenario: Tool loop returns canonical ToolResult
- **GIVEN** a tool invocation through the v2 Tool Loop
- **WHEN** it completes
- **THEN** the result is represented using the canonical v2 `ToolResult` type (not a legacy v1-only type)

### Requirement: Core Interface Coverage
The interface layer SHALL define the v4.0 stable interface surface from `doc/design/Interfaces_v4.0.md` (consistent with `doc/design/Architecture_v4.0.md`), including:

- Agent: `IAgent`（可选：`IAgentOrchestration`）
- Context: `IContext`, `IRetrievalContext`
- Tool/control planes: `IToolGateway`, `IExecutionControl`, `ISecurityBoundary`
- Plan: `IPlanner`, `IValidator`, `IRemediator`
- Cross-cutting: `IEventLog`, `IExtensionPoint`, `IConfigProvider`, `IModelAdapter`

#### Scenario: Developer implements a custom Kernel component
- **WHEN** a developer imports and implements any Kernel interface
- **THEN** the contract surface is available, typed, and usable for composition

### Requirement: Core Data Models
The interface layer SHALL provide canonical data models for v4.0, including:
`CapabilityDescriptor`, `CapabilityType`, `Envelope`, `Budget`, `DonePredicate`, `Checkpoint`, and `ContextPacket`, plus task/milestone/run result models used by the Kernel flow.

#### Scenario: Kernel and providers exchange canonical models
- **WHEN** a capability is discovered and invoked through the gateway
- **THEN** capability descriptors and envelopes use the canonical models (no protocol-specific leakage)

### Requirement: AgentBuilder Composition API
The developer API (AgentBuilder or equivalent) SHALL support composing:
Kernel defaults, strategies (planner/validator/remediator/context strategy), tools and providers, optional protocol adapters, memory, and explicit budgets.

#### Scenario: Minimal v2 build and run
- **WHEN** a developer builds an agent with v4.0 defaults and a minimal tool set
- **THEN** the agent can execute a deterministic end-to-end flow without external network dependencies

### Requirement: Optional MCP Integration Surface
The interface layer SHALL define IMCPClient and MCPToolkit, and MCP integration SHALL keep the default runtime functional when no MCP clients are configured.

#### Scenario: MCP is not configured
- **WHEN** no MCP clients are provided
- **THEN** the runtime operates with local tools only and does not attempt MCP discovery
