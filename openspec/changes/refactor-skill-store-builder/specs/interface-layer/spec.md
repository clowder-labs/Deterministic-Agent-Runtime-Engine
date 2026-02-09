## MODIFIED Requirements

### Requirement: AgentBuilder Composition API
The developer-facing agent API SHALL support composing agents via typed builders and deterministic resolution rules:

- The system SHALL provide builder variants for at least:
  - `SimpleChatAgent` (simple chat mode)
  - `FiveLayerAgent` (five-layer orchestration mode)
- Builders SHALL accept explicit component overrides (developer-injected instances) and SHALL treat them as highest precedence.
- When a required component is not explicitly provided, builders SHALL attempt to resolve it via the corresponding domain manager using the effective `Config`.
- For multi-load component categories (e.g., tools/hooks/validators), builders SHALL merge explicit components with manager-loaded components (extend semantics) while preserving injection order.
- Config enable/disable filtering MUST apply only to the manager-loaded subset and MUST NOT remove explicitly injected components.
- Builders SHALL keep `assemble_context` externally injectable so callers can customize `AssembledContext` generation.
- Builders SHALL expose a boolean skill-tool toggle (`_enable_skill_tool` via public builder API) as the only built-in skill mode switch.
- When skill-tool toggle is enabled, builders MUST auto-register `search_skill` and default context assembly MUST ignore `sys_skill`.
- When skill-tool toggle is disabled, builders MUST NOT auto-register `search_skill` and explicit `sys_skill` injection remains effective.

#### Scenario: Skill tool mode auto-registers search tool
- **GIVEN** a builder with skill-tool toggle enabled
- **WHEN** `build()` is called
- **THEN** the built context exposes `search_skill` in tool capabilities
- **AND** default assemble logic does not merge `sys_skill`

#### Scenario: Non skill tool mode preserves explicit sys_skill
- **GIVEN** a builder with skill-tool toggle disabled
- **AND** an explicit `sys_skill` is set on context
- **WHEN** default assemble logic runs
- **THEN** `search_skill` is not auto-registered
- **AND** the assembled system prompt includes the explicit `sys_skill`

#### Scenario: Custom assemble context remains pluggable
- **GIVEN** a caller injects a custom `assemble_context`
- **WHEN** the agent assembles context for model input
- **THEN** the custom strategy is used instead of the default strategy
