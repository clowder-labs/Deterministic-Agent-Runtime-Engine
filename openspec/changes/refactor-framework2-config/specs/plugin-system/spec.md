## MODIFIED Requirements
### Requirement: v2 entrypoint groups
The system SHALL define v2-specific Python entrypoint group names for extensible components.

#### Scenario: v2 groups exist for plugin categories
- **WHEN** a developer implements a plugin via entrypoints
- **THEN** there is a stable v2 group name for each category (tools/model_adapters/validators/planners/remediators/protocol_adapters/hooks, plus optional placeholders like memory/prompt_stores/skills)
