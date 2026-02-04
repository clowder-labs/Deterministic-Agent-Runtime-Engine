## MODIFIED Requirements

### Requirement: Package facades expose minimal public surface (tool domain)
The tool domain facade (`dare_framework.tool`) SHALL re-export stable kernel
interfaces, pluggable interfaces, shared types required by those contracts, and
explicitly declared supported defaults (e.g. `ToolManager`).
It MUST NOT include built-in tools.
Non-tool-domain interfaces (e.g. MCP, Skill) SHALL be exposed by their owning
domains and integrated via `IToolProvider`.

#### Scenario: Importing default tool manager
- **GIVEN** a consumer needs a supported default tool registry
- **WHEN** they import `ToolManager` from `dare_framework.tool.default_tool_manager`
- **THEN** the default registry is available without exposing built-in tools.

#### Scenario: Importing supported defaults from facade
- **GIVEN** a consumer wants the supported default registry via the facade
- **WHEN** they import `ToolManager` from `dare_framework.tool`
- **THEN** the facade exposes the default registry without exposing built-in tools.

#### Scenario: Importing public tool contracts
- **GIVEN** a consumer needs stable tool contracts
- **WHEN** they import from `dare_framework.tool`
- **THEN** only kernel/interfaces/types and supported defaults are available.
