## MODIFIED Requirements
### Requirement: Core Interface Coverage (v2)
The interface layer SHALL define the v2.0 Kernel contracts from `doc/design/Architecture_Final_Review_v2.0.md`, including:

- Kernel: `IRunLoop`, `ILoopOrchestrator`, `IExecutionControl`, `IContextManager`, `IResourceManager`, `IEventLog`, `IToolGateway`, `ISecurityBoundary`, `IExtensionPoint`
- Strategies: `IPlanner`, `IValidator`, `IRemediator`, `IContextStrategy`
- Capabilities: `IModelAdapter`, `IMemory`, `ICapabilityProvider`

#### Scenario: Developer implements a custom Kernel component
- **WHEN** a developer imports and implements any Kernel interface
- **THEN** the contract surface is available, typed, and usable for composition

### Requirement: Canonical Data Models (v2)
The interface layer SHALL provide canonical data models for v2.0, including:
`CapabilityDescriptor`, `CapabilityType`, `Envelope`, `Budget`, `DonePredicate`, `Checkpoint`, and `ContextPacket`, plus task/milestone/run result models used by the Kernel flow.

#### Scenario: Kernel and providers exchange canonical models
- **WHEN** a capability is discovered and invoked through the gateway
- **THEN** capability descriptors and envelopes use the canonical models (no protocol-specific leakage)

### Requirement: Developer API Composition Surface (v2)
The developer API (AgentBuilder or equivalent) SHALL support composing:
Kernel defaults, strategies (planner/validator/remediator/context strategy), tools and providers, optional protocol adapters, memory, and explicit budgets.

#### Scenario: Minimal v2 build and run
- **WHEN** a developer builds an agent with Kernel defaults and a minimal tool set
- **THEN** the agent can execute a deterministic end-to-end flow without external network dependencies

## REMOVED Requirements
### Requirement: v1.3-Only Primary Runtime Surface
**Reason**: v2.0 replaces `IRuntime`/`IToolRuntime`/`IContextAssembler`/`ICheckpoint` as the primary runtime surface.

#### Scenario: v1.3 surface is not required
- **WHEN** a developer uses the framework per v2.0
- **THEN** the primary execution surface is `IRunLoop` + `ILoopOrchestrator` and the old v1.3 surface is not required for functionality

