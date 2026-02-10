## Context
The framework currently exposes a flat configuration dictionary via StaticConfigProvider. The proposal introduces a hierarchical configuration model with system/user/project layers, JSON-only sources, and a typed Config model. This change focuses on interface and model design only; implementation of file loading and merging can follow in the apply stage.

## Goals / Non-Goals
- Goals:
  - Define a typed Config model that captures llm, mcp, tools, allow_tools, allow_mcps, and component enablement.
  - Specify deterministic layer resolution with system < user < project override order.
  - Provide a reload operation that returns a new effective Config without implicit live mutation.
  - Ensure runtime components rely on a single effective Config object.
- Non-Goals:
  - Implement file I/O, watchers, or concrete ConfigProvider behavior.
  - Define component-specific schemas beyond stating they are component-scoped.
  - Add hot-reload side effects in running sessions.

## Decisions
- Decision: Use JSON files as the sole configuration source for system/user/project layers.
  - Rationale: Keep parsing deterministic and aligned with the request; avoid early expansion to env/CLI sources.
- Decision: Treat allow_tools and allow_mcps as normal keys with layer override semantics (no merges).
  - Rationale: User requirement specifies that allow_tools/allow_mcps follow the same override order as other keys.
- Decision: Provide a reload method that returns a new effective Config but does not mutate existing sessions implicitly.
  - Rationale: Supports future integration while preserving deterministic session behavior.
- Decision: Represent component-specific configuration under mcp/tools as component-scoped objects keyed by component name.
  - Rationale: Allows each component to define its own schema without central coupling.
- Decision: Standardize component enablement and configuration via components.<type>.disabled and components.<type>.<name>.
  - Rationale: Provides a compact JSON structure with a clear reserved field and a predictable per-component config map.
- Decision: Require entry point components to expose a component type enum and component name.
  - Rationale: The enable/disable lookup must match a stable type/name identity in config.

## Risks / Trade-offs
- JSON-only constraint may be limiting for users who expect YAML or env overrides.
- Without a concrete path convention, implementers must document layer file locations clearly.

## JSON Example
```json
{
  "llm": {
    "endpoint": "https://api.example.com",
    "api_key": "REDACTED",
    "model": "gpt-4.1"
  },
  "components": {
    "mcp": {
      "disabled": ["legacy_mcp"],
      "default_mcp": {
        "url": "http://localhost:9000",
        "key": "mcp-key",
        "description": "Local MCP server"
      }
    }
  }
}
```

## Migration Plan
- Introduce the Config model and IConfigProvider reload interface.
- Update SessionContext and component loading to consume the effective Config.
- Add tests for layer resolution semantics once implementation begins.

## Open Questions
- None; default path conventions will be specified during implementation.
