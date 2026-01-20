## MODIFIED Requirements
### Requirement: Interface Partitioning
Core interface protocols SHALL be defined per domain in `dare_framework3/<domain>/component.py`, with reserved stable interfaces in `dare_framework3/<domain>/kernel.py`. Domain `__init__.py` files SHALL re-export the public Protocols.

#### Scenario: Finding an interface
- **WHEN** a contributor looks for `IToolGateway`
- **THEN** it is defined in `dare_framework3/tool/component.py` and re-exported from `dare_framework3.tool`.

### Requirement: Interface Intent Documentation
Each core interface and each abstract method SHALL include a concise design-intent docstring or comment that explains its role, trust boundary, or layer responsibility.

#### Scenario: Reading an interface contract
- **WHEN** a contributor reads `ISecurityBoundary`
- **THEN** the interface includes a short note describing its enforcement role per the design docs.

## REMOVED Requirements
### Requirement: Tool Registry Interface
**Reason**: v3.2 removes the dedicated tool registry interface in favor of gateway-level capability metadata.
**Migration**: use `IToolGateway.list_capabilities` and `ToolDefinition` types to access tool metadata.

#### Scenario: Legacy registry access
- **WHEN** SecurityBoundary needs tool metadata
- **THEN** it uses `IToolGateway` capability listings instead of `IToolRegistry`.

### Requirement: Tool Registry Minimal Contract
**Reason**: The minimal registry contract is no longer part of the v3.2 interface surface.
**Migration**: rely on `ToolDefinition` and gateway-provided capability descriptors.

#### Scenario: Resolving a tool by name
- **WHEN** a component needs to locate a tool definition
- **THEN** it matches against the gateway-provided capability list.
