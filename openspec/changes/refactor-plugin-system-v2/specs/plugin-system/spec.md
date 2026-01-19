## ADDED Requirements

### Requirement: v2 entrypoint groups
The system SHALL define v2-specific Python entrypoint group names for extensible components.

#### Scenario: v2 groups exist for plugin categories
- **WHEN** a developer implements a plugin via entrypoints
- **THEN** there is a stable v2 group name for each category (tools/model_adapters/validators/planners/remediators/protocol_adapters/hooks/config_providers, plus optional placeholders like memory/prompt_stores/skills)

### Requirement: Manager-driven loading rules
The system SHALL provide component manager interfaces for entrypoint-driven extensibility, and SHALL document each manager’s loading rules and design goals.

Default manager implementations MAY be no-ops initially, but MUST preserve the interface surface and MUST describe the intended behavior in docstrings/comments.

#### Scenario: Model adapter selection rules are documented
- **GIVEN** a model adapter manager interface
- **WHEN** a developer reads its documentation
- **THEN** it explains that model adapters are selected by configured component name (entrypoint name)

#### Scenario: Validator loading rules are documented
- **GIVEN** a validator manager interface
- **WHEN** a developer reads its documentation
- **THEN** it explains that validators load as an ordered, config-filtered collection (sorted by `order`)
