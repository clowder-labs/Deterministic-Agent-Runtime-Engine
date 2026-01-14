# Change: Add layered runtime configuration and session config injection

## Why
We need a standard configuration model that spans system/user/project levels, covers runtime surfaces (LLM, MCP, tool allowlists, component toggles), and flows into each agent session. Today ConfigProvider exists but lacks a schema, merge rules, or session wiring, making it hard to test, validate, or configure validators/tools/hooks and composite tools via config.

## What Changes
- Define a layered configuration schema (system → project → user → session) covering model/MCP settings, tool/skill/validator/hook enablement, and allow/deny lists.
- Expand ConfigProvider to load/merge layers, validate against the schema, and surface the effective session config.
- Wire session initialization to attach the effective config into SessionContext so runtime/components can consume it.
- Allow component selection (validators, tools, hooks, composite tools) to be driven by config entries in addition to entry point discovery.

## Impact
- Affected specs: configuration, core-runtime (session context)
- Affected code: ConfigProvider, AgentBuilder/session init, component managers loading from config, composite tool assembly, tests
