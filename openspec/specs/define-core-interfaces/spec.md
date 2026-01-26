# define-core-interfaces Specification

## Purpose
TBD - created by archiving change refactor-layered-structure. Update Purpose after archive.
## Requirements
### Requirement: Interface Partitioning
Core interface protocols SHALL be defined per domain. Stable kernel interfaces (Layer 0) SHALL live in `dare_framework3_3/<domain>/kernel.py`, and pluggable interfaces SHALL live in `dare_framework3_3/<domain>/component.py`. Domain `__init__.py` files SHALL re-export the public Protocols.

#### Scenario: Finding an interface
- **WHEN** a contributor looks for `IToolGateway`
- **THEN** it is defined in `dare_framework3_3/tool/kernel.py` and re-exported from `dare_framework3_3.tool`.

### Requirement: Interface Intent Documentation
Each core interface and each abstract method SHALL include a concise design-intent docstring that declares scope (`[Kernel]`, `[Component]`, or `[Types]`) and the intended usage scenario.

#### Scenario: Reading an interface contract
- **WHEN** a contributor reads `ISecurityBoundary`
- **THEN** the interface includes scope tags and a short note describing its enforcement role.

### Requirement: Kernel Interface Coverage
Kernel interfaces SHALL include the stable contracts needed by the agent runtime, including:
`IContextManager`, `IResourceManager`, `IToolGateway`, `IExecutionControl`, `IEventLog`, `IExtensionPoint`, `IConfigProvider`, and `ISecurityBoundary`.

#### Scenario: Kernel coverage for config/hook/tool
- **WHEN** a contributor inspects kernel interfaces for config, hook, and tool domains
- **THEN** `IConfigProvider`, `IExtensionPoint`, `IToolGateway`, and `IExecutionControl` are defined in their respective `kernel.py` files.

