## MODIFIED Requirements

### Requirement: Config Model Structure
The Config model SHALL include at least the following top-level fields: llm, mcp, tools, allow_tools, allow_mcps, components, workspace_dir, and user_dir. The llm field MUST support connectivity configuration such as adapter, endpoint, api_key, model, and optional proxy settings (http, https, no_proxy, use_system_proxy, disabled). When proxy.disabled is true, proxy settings MUST be treated as disabled. Explicit proxy configuration and system proxy selection MUST be mutually exclusive in the effective model. The mcp and tools fields MUST support component-scoped configuration objects keyed by component name. The components field MUST support enable/disable flags and per-component configuration for entry point components by type and name (including validator, hook, skill, memory, model_adapter, tool, mcp, and prompt).

The Config model MUST NOT require top-level skill mode/path fields such as `skill_mode`, `skill_paths`, or `initial_skill_path`.

Skill filesystem discovery MUST be derived from `workspace_dir` and `user_dir` by the skill loading layer.

#### Scenario: Skill loading relies on workspace/user dirs only
- **GIVEN** an effective Config containing `workspace_dir` and `user_dir`
- **WHEN** the runtime initializes skill loading
- **THEN** skill loading derives filesystem roots from those directories
- **AND** no `skill_mode`, `skill_paths`, or `initial_skill_path` fields are required in Config
