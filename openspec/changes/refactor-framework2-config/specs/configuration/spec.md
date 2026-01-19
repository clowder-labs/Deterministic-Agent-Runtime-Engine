## MODIFIED Requirements
### Requirement: ConfigManager merging and access
ConfigManager SHALL load or accept all available layers, merge them into an effective Config, and expose namespaced getters for components and runtime logic.

#### Scenario: Namespaced lookup
- **WHEN** a component requests `tools.enable` via ConfigManager (for example, `get` or `get_namespace`)
- **THEN** it receives the effective merged value for that namespace without needing to parse raw sources

### Requirement: Configuration manager interface
The system SHALL define a ConfigManager interface/class that returns configuration values by key or namespace for component initialization.

#### Scenario: Component loads configuration
- **WHEN** a component requests configuration during `init()`
- **THEN** the ConfigManager MUST return the configured values or defaults
