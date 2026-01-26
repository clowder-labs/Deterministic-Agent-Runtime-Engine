# core-config Specification

## Purpose
TBD - created by archiving change consolidate-config-to-core. Update Purpose after archive.
## Requirements
### Requirement: ComponentType in contracts
The `ComponentType` enum SHALL be located in `dare_framework/infra/component.py` as a cross-domain shared type.

#### Scenario: All layers import ComponentType from infra
- **WHEN** any layer (config, builder, kernel defaults, components) needs `ComponentType`
- **THEN** it MUST import from `dare_framework.infra.component`.

### Requirement: Core config module location
The configuration management module SHALL be located under `dare_framework/core/config/` as part of the Kernel (Layer 0).

#### Scenario: Developer locates config module
- **WHEN** a developer looks for configuration management code
- **THEN** it MUST be found under `dare_framework/core/config/` (not as a sibling of `core/`)

### Requirement: ConfigManager provides layered merge
The `ConfigManager` class SHALL support layered configuration merge with precedence order: system < project < user < session.

#### Scenario: Session overrides project config
- **GIVEN** a config key defined in both project and session layers
- **WHEN** `ConfigManager.effective()` is called
- **THEN** the session layer value MUST override the project layer value

### Requirement: Immutable Config snapshots
The `Config` object returned by `ConfigManager.effective()` SHALL be immutable (frozen dataclass).

#### Scenario: Config cannot be mutated
- **GIVEN** an effective `Config` object
- **WHEN** code attempts to modify a field
- **THEN** a `FrozenInstanceError` MUST be raised

### Requirement: No plugin lifecycle for config
Configuration management SHALL NOT depend on the plugin lifecycle (`IComponent.init/register/close`).

#### Scenario: Config available before component init
- **GIVEN** the runtime is starting
- **WHEN** config is loaded
- **THEN** it MUST complete before any `IComponent.init()` calls

