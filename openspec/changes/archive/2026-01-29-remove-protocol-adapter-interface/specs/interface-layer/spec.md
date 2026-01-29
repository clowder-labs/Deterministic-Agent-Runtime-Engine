## MODIFIED Requirements
### Requirement: Optional MCP Integration Surface
The interface layer SHALL NOT define protocol adapter interfaces. Protocol adapter surfaces are deferred until a dedicated integration is specified.

#### Scenario: MCP is not configured
- **WHEN** no MCP clients are provided
- **THEN** the runtime operates with local tools only and does not attempt protocol discovery
