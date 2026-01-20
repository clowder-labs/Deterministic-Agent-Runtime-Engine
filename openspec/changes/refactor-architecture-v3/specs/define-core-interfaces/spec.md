## MODIFIED Requirements
### Requirement: Interface Partitioning
Core interface protocols SHALL be defined per domain. Stable kernel interfaces (Layer 0) SHALL live in `dare_framework3_3/<domain>/kernel.py`, and pluggable interfaces SHALL live in `dare_framework3_3/<domain>/component.py`. Domain `__init__.py` files SHALL re-export the public Protocols.

#### Scenario: Finding an interface
- **WHEN** a contributor looks for `IToolGateway`
- **THEN** it is defined in `dare_framework3_3/tool/kernel.py` and re-exported from `dare_framework3_3.tool`.

### Requirement: Kernel Interface Coverage
Kernel interfaces SHALL include the stable contracts needed by the agent runtime, including:
`IContextManager`, `IResourceManager`, `IToolGateway`, `IExecutionControl`, `IEventLog`, `IExtensionPoint`, `IConfigProvider`, and `ISecurityBoundary`.

#### Scenario: Kernel coverage for config/hook/tool
- **WHEN** a contributor inspects kernel interfaces for config, hook, and tool domains
- **THEN** `IConfigProvider`, `IExtensionPoint`, `IToolGateway`, and `IExecutionControl` are defined in their respective `kernel.py` files.

### Requirement: Interface Intent Documentation
Each core interface and each abstract method SHALL include a concise design-intent docstring that declares scope (`[Kernel]`, `[Component]`, or `[Types]`) and the intended usage scenario.

#### Scenario: Reading an interface contract
- **WHEN** a contributor reads `ISecurityBoundary`
- **THEN** the interface includes scope tags and a short note describing its enforcement role.

## REMOVED Requirements
### Requirement: Tool Registry Interface
**Reason**: v3.3 removes the dedicated tool registry interface in favor of gateway-level capability metadata.
**Migration**: use `IToolGateway.list_capabilities` and `ToolDefinition` types to access tool metadata.

#### Scenario: Legacy registry access
- **WHEN** SecurityBoundary needs tool metadata
- **THEN** it uses `IToolGateway` capability listings instead of `IToolRegistry`.

### Requirement: Tool Registry Minimal Contract
**Reason**: The minimal registry contract is no longer part of the v3.3 interface surface.
**Migration**: rely on `ToolDefinition` and gateway-provided capability descriptors.

#### Scenario: Resolving a tool by name
- **WHEN** a component needs to locate a tool definition
- **THEN** it matches against the gateway-provided capability list.
