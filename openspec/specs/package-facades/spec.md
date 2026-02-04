# package-facades Specification

## Purpose
TBD - created by archiving change refactor-package-facades. Update Purpose after archive.
## Requirements
### Requirement: Package facades
Domain packages (`dare_framework3_3.agent`, `dare_framework3_3.context`, `dare_framework3_3.model`, `dare_framework3_3.memory`, `dare_framework3_3.tool`, `dare_framework3_3.plan`, `dare_framework3_3.event`, `dare_framework3_3.hook`, `dare_framework3_3.security`, `dare_framework3_3.config`, `dare_framework3_3.utils`) SHALL re-export the symbols intended for public use via `__init__.py` and `__all__ = [...]`. Separate `interfaces` or `types` facade packages SHALL NOT be required.

#### Scenario: Domain package exports public members
- **GIVEN** a domain package directory with submodules
- **WHEN** the package is imported
- **THEN** its `__init__.py` re-exports the classes and objects intended for public use.

### Requirement: No direct definitions in initializers
`__init__.py` files SHALL NOT contain class or function definitions.

#### Scenario: Definitions stay in submodules
- **GIVEN** a need for a new class in a package
- **WHEN** the developer implements it
- **THEN** it is defined in a separate submodule (like `types.py` or `component.py`), not in `__init__.py`.

### Requirement: Documentation in initializers
Every `__init__.py` file SHALL have a docstring or comments describing the package's purpose.

#### Scenario: Package has a docstring
- **GIVEN** an `__init__.py` file
- **THEN** it starts with a docstring or includes comments explaining what the package contains and its responsibility.

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

