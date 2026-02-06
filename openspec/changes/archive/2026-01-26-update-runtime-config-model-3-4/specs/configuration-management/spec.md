## MODIFIED Requirements
### Requirement: Effective Config Object
The ConfigProvider SHALL return a single effective Config object that represents the resolved configuration. The effective Config MUST be immutable and safe to share across runtime components; providers MAY wrap it in a ConfigSnapshot that carries metadata such as hash or source layers.

#### Scenario: Components read from effective Config
- **WHEN** a component requests configuration
- **THEN** it receives values from the immutable Config snapshot produced by the ConfigProvider

### Requirement: Config Model Structure
The Config model SHALL include at least the following top-level fields: llm, mcp, tools, allow_tools, allow_mcps, components, workspace_dir, and user_dir. The llm field MUST support connectivity configuration such as adapter, endpoint, api_key, model, and optional proxy settings (http, https, no_proxy, use_system_proxy, disabled). When proxy.disabled is true, proxy settings MUST be treated as disabled. Explicit proxy configuration and system proxy selection MUST be mutually exclusive in the effective model. The mcp and tools fields MUST support component-scoped configuration objects keyed by component name. The components field MUST support enable/disable flags and per-component configuration for entry point components by type and name (including validator, hook, skill, memory, model_adapter, tool, mcp, and prompt).

#### Scenario: LLM connectivity fields available
- **WHEN** the effective Config is produced
- **THEN** the llm field can provide adapter, endpoint, api_key, model, and optional proxy values

#### Scenario: Proxy disabled takes precedence
- **GIVEN** llm.proxy.disabled is true
- **WHEN** the effective Config is produced
- **THEN** the model adapter treats proxy as disabled regardless of other proxy fields
