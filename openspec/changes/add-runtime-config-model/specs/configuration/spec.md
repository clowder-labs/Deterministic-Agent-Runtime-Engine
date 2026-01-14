## ADDED Requirements
### Requirement: Layered runtime configuration
The system SHALL support a layered configuration model with system, project, user, and session overrides that cover runtime settings (llm, mcp, tools, skills, validators, hooks, allow/deny lists, composite_tools, runtime budgets).

#### Scenario: Merge precedence
- **WHEN** system, project, user, and session configs all define a value
- **THEN** the effective config SHALL resolve by precedence `system < project < user < session` and be schema-validated

### Requirement: ConfigProvider merging and access
ConfigProvider SHALL load all available layers, validate them against the configuration schema, merge them into an effective config, and expose namespaced getters for components and runtime logic.

#### Scenario: Namespaced lookup
- **WHEN** a component requests `tools.enable` via ConfigProvider
- **THEN** it receives the effective merged value for that namespace without needing to parse raw files

### Requirement: Session context carries effective config
Session initialization SHALL attach the effective merged config (or a hash + source metadata) into SessionContext so runtime loops and components can consume consistent settings.

#### Scenario: Session exposes config snapshot
- **WHEN** a session starts
- **THEN** SessionContext includes the effective config snapshot (read-only) and an event log entry records the config hash for audit

### Requirement: Config-driven component selection
The system SHALL allow validators, tools, hooks (and composite tools) to be enabled, disabled, or composed based on configuration entries in addition to entry point discovery defaults.

#### Scenario: Composite tool from config
- **WHEN** config defines a composite tool recipe referencing existing tools
- **THEN** the component loader assembles and registers that composite tool so it is invokable during plan/execute loops
