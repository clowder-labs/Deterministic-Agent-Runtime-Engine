## Context
- Component managers load components via entry points and order by `order`, but config-driven enable/disable and composite tool assembly need clearer rules to avoid clashes with manual injection.
- We want minimal surface: config filters, simple composite tool recipes (sequential), and lifecycle ownership boundaries.

## Goals / Non-Goals
- Goals: Config-aware selection (enable/disable) for all manager types; composite tool assembly from config; lifecycle ownership clarified; defaults remain backward-compatible when no config is provided.
- Non-Goals: Advanced dependency resolution, dynamic reload, or complex composite graph orchestration.

## Design
- Config filtering: each manager reads its namespace (e.g., `tools.enable/disable`, `validators.enable/disable`) from ConfigProvider; `enable` restricts to a whitelist, `disable` removes by name; names derive from component `.name` or class name fallback. Absent lists → no filtering.
- Composite tools: config accepts `composite_tools: [ { name, description?, steps: [ { tool, input? } ] } ]`; ToolManager assembles a sequential CompositeTool that executes steps in order, failing fast on missing tools or malformed steps. Validation: `name` non-empty string, `steps` is list, every step has `tool` string; optional `input` must be a dict if present.
- Lifecycle: Managers call `init`/`register` only for components they instantiate via discovery; externally provided components (manual injection into builder/registries) are registered but not closed. A future `close_all()` would only apply to managed components; current scope documents the ownership boundary.

## Open Questions
- Should config also support ordering overrides? (Out of scope for minimal pass.)
- Should composite tools expose risk level/timeout overrides? (Assume defaults; revisit if needed.)
