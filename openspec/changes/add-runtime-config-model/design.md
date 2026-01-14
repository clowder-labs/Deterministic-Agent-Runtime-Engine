## Context
- ConfigProvider exists but lacks a schema, merge precedence, or session wiring. Components are discovered via entry points only, and SessionContext does not expose runtime config.
- Requirements call for layered config (system/user/project/session) that includes LLM, MCP, allowlists, and component toggles, plus making validators/tools/hooks configurable and enabling composite tools.

## Goals / Non-Goals
- Goals: Define a minimal schema and merge rules; expose effective config in SessionContext; allow config-driven selection/assembly of validators/tools/hooks (including composites); keep defaults working without config.
- Non-Goals: Full UI for editing config; remote config service; advanced policy language.

## Decisions
- Layer precedence: system < project < user < session overrides; missing layers default to empty.
- Schema sections: `llm`, `mcp`, `tools`, `skills`, `validators`, `hooks`, `allow`, `deny`, `composite_tools`, plus `runtime` metadata (timeouts/budgets).
- Session snapshot: SessionContext holds `effective_config` (read-only dict) derived at session init; event log records a hash + layer sources for audit.
- Component control: Managers accept config to enable/disable components and to assemble composite tools from config-defined recipes referencing existing tools.

## Risks / Trade-offs
- Config sprawl: keep schema minimal and optional; defaults must preserve current deterministic flow.
- Composite tools could complicate testing; mitigate by constraining recipe shape (sequence/inputs) and providing fixtures.

## Open Questions
- Do we need live reload of config between milestones? (Assume no for now; per-session snapshot.)
- What is the minimal composite tool recipe (sequence vs fan-out)? (Assume sequential composition.)
