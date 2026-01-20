## RENAMED Requirements
- FROM: `### Requirement: Shared types are v2-aligned`
- TO: `### Requirement: Shared types are domain-owned`
- FROM: `### Requirement: AgentBuilder Composition API`
- TO: `### Requirement: Agent Composition API`

## MODIFIED Requirements
### Requirement: Shared types are domain-owned
The system SHALL locate canonical types within their owning domains (context, tool, plan, event, hook, security, model, memory, config) and SHALL use them across kernel, components, and examples.

#### Scenario: Tool loop returns canonical ToolResult
- **GIVEN** a tool invocation through the v3 Tool Loop
- **WHEN** it completes
- **THEN** the result is represented using the canonical `ToolResult` type from `dare_framework3/tool/types.py`.

### Requirement: Core Interface Coverage
The domain component layer SHALL define the Kernel contracts and component interfaces, including:

- Context: `IContextManager`, `IContextStrategy`, `IResourceManager`
- Model: `IModelAdapter`
- Memory: `IMemory`, `IPromptStore`
- Tool: `IToolGateway`, `ITool`, `ISkill`, `ICapabilityProvider`, `IProtocolAdapter`, `IMCPClient`, `IExecutionControl`
- Plan: `IPlanner`, `IValidator`, `IRemediator`
- Event: `IEventLog`, `IEventListener`
- Hook: `IExtensionPoint`, `IHook`
- Security: `ISecurityBoundary`
- Config: `IConfigProvider`

#### Scenario: Developer implements a custom component
- **WHEN** a developer imports and implements any domain interface
- **THEN** the contract surface is available, typed, and usable for composition.

### Requirement: Core Data Models
The component layer SHALL provide canonical data models for v3, including:
`CapabilityDescriptor`, `CapabilityType`, `Envelope`, `RunContext`, `Budget`, `ResourceType`, `ToolDefinition`, `ToolResult`, `ExecutionSignal`, `Checkpoint`, `Task`, `Milestone`, `RunResult`, `Event`, `RuntimeSnapshot`, `HookPhase`, `RiskLevel`, `PolicyDecision`, `TrustedInput`, and `SandboxSpec`.

#### Scenario: Kernel and providers exchange canonical models
- **WHEN** a capability is discovered and invoked through the gateway
- **THEN** capability descriptors and envelopes use the canonical models (no protocol-specific leakage).

### Requirement: Agent Composition API
The developer-facing agent API SHALL support direct composition of core components by passing optional overrides into agent constructors, with defaults created when omitted.

#### Scenario: Minimal v3 build and run
- **WHEN** a developer constructs a `FiveLayerAgent` with a model adapter and tools
- **THEN** the agent can execute a deterministic end-to-end flow without external builder scaffolding.
