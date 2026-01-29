## MODIFIED Requirements

### Requirement: Framework-Backed Coding Agent Example
The example agent SHALL be built using the developer API and SHALL register tools (directly or via tool-group providers) in a way that exercises the Kernel `IToolGateway` boundary.

#### Scenario: Example agent instantiation
- **WHEN** a developer instantiates the example agent
- **THEN** it composes Kernel defaults, a deterministic planner/model adapter, and a minimal tool set
