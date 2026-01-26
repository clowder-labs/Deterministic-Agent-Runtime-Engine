## MODIFIED Requirements
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
