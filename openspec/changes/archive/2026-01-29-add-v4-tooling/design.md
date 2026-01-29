## Context
`dare_framework3_4` is the v4.0 base but currently lacks the tool runtime described in the v4.0 design docs: there are no v4-aligned tool interfaces/types, no default gateway/providers, and no built-in file tools. Commit `a1d8ad5c6` (branch `add_tools`) added a minimal workspace file toolset to `dare_framework`, but it needs to be adapted to the v4.0 layout and configuration semantics before landing in `dare_framework3_4`.

## Goals / Non-Goals
- Goals:
  - Implement v4.0-aligned tool interfaces/types in `dare_framework3_4` (gateway, execution control, providers, tools).
  - Provide built-in workspace file tools (`read_file`, `search_code`, `write_file`, `edit_line`) with guardrails and deterministic behavior.
  - Enforce `workspace_roots` from the v4.0 config shape and support `tools.<tool_name>` guardrail configuration.
  - Keep tool listings for model calls traceable to the trusted gateway registry.
- Non-Goals:
  - Implement the full five-layer runtime or orchestration loops in `dare_framework3_4`.
  - Add network tools or patch-based editors.
  - Introduce new external dependencies.

## Decisions
- **Domain layout**: Add `tool/types.py`, `tool/interfaces.py`, and expand `tool/component.py` to match v4.0 contracts; keep default implementations under `tool/internal/` (per v4.0 file layout conventions).
- **Risk enum placement**: Define the risk level enum in `dare_framework3_4/security/types.py` and reference it from tool types, aligning with v4.0 separation of security concerns.
- **Trusted tool listings**: Implement an `IToolProvider` that builds `Prompt.tools` from `IToolGateway.list_capabilities()` to ensure tool definitions are derived from the trusted registry (no LLM-sourced tool defs).
- **Config compatibility**: `RunContext.config` should accept either a v4.0 `Config` object or a dict; tool utilities read `workspace_roots` and `tools.<tool_name>` with safe defaults when missing.
- **Workspace enforcement**: Resolve paths against canonical `workspace_roots`, reject escapes (including symlink traversal), and return relative paths in tool outputs.
- **Determinism & guardrails**: `search_code` walks files deterministically (sorted dirs/files), enforces `max_results` and `max_file_bytes`, and returns `truncated` when capped. File writes use atomic replace semantics.
- **Evidence emission**: Successful tool calls emit evidence entries with stable IDs, tool name, and target path.
- **Opt-in wiring**: `SimpleChatAgent` remains opt-in for tool providers; no automatic wiring unless the caller supplies a provider.
- **Public exports**: Built-in file tools are exported publicly from the v4.0 tool package for explicit use.
- **Doc update target**: Update `examples/base_tool/README.md` to reference the built-in v4.0 toolset and config knobs.

## Risks / Trade-offs
- The file tools are available in `dare_framework3_4` even though the simple chat agent does not execute tools; consumers must explicitly wire the gateway/provider in higher-level orchestration.
- Strict guardrails may block large files by default; configurability mitigates this.

## Migration Plan
1. Add v4.0 tool interfaces/types and risk enum in `dare_framework3_4`.
2. Port default tool runtime components and basic tools into `dare_framework3_4/tool/internal`.
3. Port and adapt the workspace file tools + shared file utils.
4. Wire a trusted tool provider for `Context.listing_tools()`.
5. Add unit tests and update docs.
