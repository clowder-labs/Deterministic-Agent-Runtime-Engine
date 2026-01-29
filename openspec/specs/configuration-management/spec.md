# configuration-management Specification

## Purpose
TBD - created by archiving change hierarchical-config-management. Update Purpose after archive.
## Requirements
### Requirement: Configuration Layers and JSON Sources
The system SHALL support three configuration layers: system, user, and project. Each layer MUST be loaded from JSON-formatted configuration files.

#### Scenario: Load layered JSON config files
- **WHEN** the configuration system initializes
- **THEN** it loads system, user, and project JSON configuration files as separate layers

### Requirement: Deterministic Layer Override Order
The system SHALL resolve configuration by applying layers in the order system < user < project, with later layers overriding earlier ones for the same key.

#### Scenario: Project overrides user and system values
- **GIVEN** a key exists in system and user layers
- **AND** the same key is defined in the project layer
- **WHEN** the effective configuration is computed
- **THEN** the project value is used

### Requirement: Effective Config Object
The ConfigProvider SHALL return a single effective `Config` object that represents the resolved configuration. The effective `Config` MUST be immutable and safe to share across runtime components.

#### Scenario: Provider returns Config directly
- **WHEN** the configuration provider returns the effective configuration
- **THEN** it returns an immutable `Config` object directly (not wrapped in a `ConfigSnapshot`)

### Requirement: allowtools and allowmcps Override Semantics
The allowtools and allowmcps settings SHALL be treated as normal configuration keys and follow the same layer override order (system < user < project). They MUST NOT be merged across layers unless explicitly specified by the effective layer.

#### Scenario: Project allowtools overrides lower layers
- **GIVEN** allowtools is defined in system and user layers
- **AND** allowtools is defined in the project layer
- **WHEN** the effective configuration is computed
- **THEN** the project allowtools value replaces the lower-layer values

### Requirement: Config Model Structure
The Config model SHALL include at least the following top-level fields: llm, mcp, tools, allowtools, allowmcps, components, workspace_dir, and user_dir. The llm field MUST support connectivity configuration such as adapter, endpoint, api_key, model, and optional proxy settings (http, https, no_proxy, use_system_proxy, disabled). When proxy.disabled is true, proxy settings MUST be treated as disabled. Explicit proxy configuration and system proxy selection MUST be mutually exclusive in the effective model. The mcp and tools fields MUST support component-scoped configuration objects keyed by component name. The components field MUST support enable/disable flags and per-component configuration for entry point components by type and name (including validator, hook, skill, memory, model_adapter, tool, mcp, and prompt).

#### Scenario: LLM connectivity fields available
- **WHEN** the effective Config is produced
- **THEN** the llm field can provide adapter, endpoint, api_key, model, and optional proxy values

#### Scenario: Proxy disabled takes precedence
- **GIVEN** llm.proxy.disabled is true
- **WHEN** the effective Config is produced
- **THEN** the model adapter treats proxy as disabled regardless of other proxy fields

### Requirement: Component Enablement Configuration
The system SHALL support a uniform enable/disable configuration for all entry point components using a type-scoped structure. The components.<type>.disabled list identifies disabled component names. The default behavior MUST be enabled when a name is absent from components.<type>.disabled.

#### Scenario: Component enabled by default
- **GIVEN** a component is discovered via entry points
- **AND** the component name is not listed in components.<type>.disabled
- **WHEN** the component manager evaluates configuration
- **THEN** the component is treated as enabled

### Requirement: Component Configuration Structure
The components.<type> map SHALL store per-component configuration objects keyed by component name. The configuration system MUST treat reserved keys under components.<type> as non-instance entries.

#### Scenario: Component instance config is stored under component name
- **GIVEN** a component type with a configured instance
- **WHEN** the effective Config is computed
- **THEN** the per-component configuration is available at components.<type>.<name>

### Requirement: Component Identity for Configuration
Each entry point component implementation SHALL expose a component type and name for configuration lookup.

The canonical identity surface SHALL be `infra.IComponent.component_type` and `infra.IComponent.name`, and SHALL use the shared `ComponentType` enum for types.

#### Scenario: Component exposes type for config lookup
- **WHEN** a component is discovered via entry points or provided by a manager
- **THEN** config filtering can read its `component_type` and `name` for enable/disable evaluation

### Requirement: Component Type Enumeration
The component type enum MUST include validator, memory, model_adapter, tool, skill, mcp, hook, and prompt to cover all entry point component categories managed by BaseComponentManager.

#### Scenario: Component type enum includes entry point categories
- **WHEN** a component is registered via entry points
- **THEN** its type matches one of the enumerated component types

### Requirement: MCP Configuration in Config Model
The Config model SHALL support MCP connection configuration keyed by MCP name so the MCP manager can construct MCP clients and MCP-backed tools.

#### Scenario: MCP manager reads MCP config by name
- **WHEN** the MCP manager initializes
- **THEN** it can read MCP configuration from Config.mcp using the MCP name

### Requirement: Reload Interface
The ConfigProvider SHALL expose a reload operation that re-reads configuration files and returns a new effective Config object. Reloading MUST NOT implicitly mutate existing running sessions unless the caller chooses to replace the active Config.

#### Scenario: Reload returns a new effective Config
- **WHEN** reload is invoked
- **THEN** the provider re-reads the layered JSON files and returns a new effective Config object

### Requirement: Session Context Carries Effective Config
The SessionContext SHALL store the effective Config for the session lifecycle, and subsequent components MUST treat that Config as the source of truth.

#### Scenario: SessionContext includes effective Config
- **WHEN** a session starts
- **THEN** SessionContext holds the effective Config produced by the ConfigProvider

### Requirement: Config enablement helpers accept components
The `Config` model SHALL expose helper APIs that accept concrete component instances for enablement evaluation and filtering.

#### Scenario: Filter manager-loaded components by config
- **GIVEN** a list of components loaded by a manager
- **WHEN** config filters the list
- **THEN** only enabled components remain, using each component's type and name for lookup

### Requirement: Prompt configuration fields
The Config model SHALL include optional top-level fields used by prompt management:
- `prompt_store_path_pattern`
- `default_prompt_id`

`prompt_store_path_pattern` MUST be a string path pattern used by the default prompt store to locate prompt manifests.
`default_prompt_id` MAY be omitted or null; when set, it identifies the prompt_id used as the default system prompt.

#### Scenario: Prompt config values are exposed
- **GIVEN** prompt configuration values are set in config layers
- **WHEN** the effective Config is produced
- **THEN** it exposes `prompt_store_path_pattern` and `default_prompt_id` for prompt resolution

