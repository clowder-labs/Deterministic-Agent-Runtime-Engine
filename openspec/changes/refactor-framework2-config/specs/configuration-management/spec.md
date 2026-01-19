## MODIFIED Requirements
### Requirement: Configuration Layers and JSON Sources
The system SHALL support four configuration layers: system, project, user, and session. Each layer MAY be loaded from JSON configuration files or supplied programmatically as dictionaries.

#### Scenario: Load layered JSON config files
- **WHEN** the configuration system initializes
- **THEN** it loads or receives system, project, user, and session layers as separate sources

### Requirement: Deterministic Layer Override Order
The system SHALL resolve configuration by applying layers in the order system < project < user < session, with later layers overriding earlier ones for the same key.

#### Scenario: Project overrides user and system values
- **GIVEN** a key exists in system and user layers
- **AND** the same key is defined in the project layer
- **WHEN** the effective configuration is computed
- **THEN** the project value is used

#### Scenario: Session overrides project config
- **GIVEN** a key exists in project and session layers
- **WHEN** the effective configuration is computed
- **THEN** the session value is used

### Requirement: Effective Config Object
The ConfigManager SHALL return a single effective Config object that represents the resolved configuration. All runtime components MUST rely on this effective Config object for configuration access.

#### Scenario: Components read from effective Config
- **WHEN** a component requests configuration
- **THEN** it receives values from the effective Config object produced by the ConfigManager

### Requirement: Reload Interface
The ConfigManager SHALL expose a reload operation that re-reads or re-merges configuration sources and returns a new effective Config object. Reloading MUST NOT implicitly mutate existing running sessions unless the caller chooses to replace the active Config.

#### Scenario: Reload returns a new effective Config
- **WHEN** reload is invoked
- **THEN** the manager re-reads the layered sources and returns a new effective Config object
