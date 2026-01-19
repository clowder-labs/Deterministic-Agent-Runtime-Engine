## Context
The `add_tools` branch introduces a minimal workspace file toolset under `dare_framework/components/tools/` with:
- workspace-root enforcement (`workspace_roots`)
- bounded I/O (`max_bytes`, `max_results`, ignore dirs)
- deterministic ordering
- atomic writes (temp + rename)

This change ports that capability into `dare_framework2/` without importing `dare_framework/` implementation details, and aligns with the v2 tool gateway + provider model.

## Goals / Non-Goals
- Goals:
  - Provide `read_file`, `search_code`, `write_file`, `edit_line` for `dare_framework2`.
  - Enforce workspace-root boundaries and resource limits with safe defaults.
  - Keep outputs deterministic and avoid new dependencies.
  - Preserve auditability via evidence emission.
- Non-Goals:
  - Implement patch/diff editing, binary file ops, or network tools.
  - Implement a real blocking HITL UI (existing `FileExecutionControl.wait_for_human` remains a stub).
  - Introduce a new plugin/entrypoint discovery system for `dare_framework2` in this change.

## Decisions
### Tool placement and types
- Implement tools under `dare_framework2/tool/impl/` alongside `RunCommandTool` and `NoOpTool`.
- Tools will implement `dare_framework2.tool.interfaces.ITool` and return canonical `ToolResult` (no exceptions escaping tool execution).
- Capabilities are exposed via `NativeToolProvider` as `tool:<name>` IDs; the underlying tool `name` stays as `read_file`, etc.

### Config and workspace roots
- Tools read:
  - `workspace_roots` from `context.config.workspace_roots` when available
  - per-tool guardrails from `context.config.tools.get(tool_name, {})` when available
  - safe defaults when config is absent or invalid
- To make this usable through the runtime, extend `dare_framework2.tool.impl.RunContextState` to carry an optional `config` field and set it from `AgentBuilder` at build time.

### Guardrails and determinism
- Guardrails match the `add_tools` commit defaults:
  - `read_file.max_bytes`: 1_000_000
  - `write_file.max_bytes`: 1_000_000
  - `edit_line.max_bytes`: 1_000_000
  - `search_code.max_results`: 50
  - `search_code.max_file_bytes`: 1_000_000
  - `search_code.ignore_dirs`: [".git", "node_modules", "__pycache__", ".venv", "venv"]
- `search_code` traversal order is deterministic (sorted dirs/files; results ordered by relative path then line).
- `write_file` and `edit_line` use atomic replace semantics.

### Errors and audit evidence
- Failures return `ToolResult(success=False, error=...)` with stable, non-sensitive messages (prefer short error codes).
- Success emits at least one `Evidence` record describing the operation (kind + relative path).

## Risks / Trade-offs
- `dare_framework2` currently lacks a complete config provider/session config wiring; this change only ensures tools *can* receive config via `RunContextState`.
- Any non-READ_ONLY tool triggers the default approval gate, but current execution control is non-blocking; users should not run with untrusted prompts in production without a real HITL controller.

## Migration Plan
- Add tool implementations + shared file/path utilities.
- Wire config into `RunContextState` and builder composition.
- Add unit tests and validate behavior against the spec delta.
- Optionally add a small `dare_framework2` example snippet showing how to include the toolset.

## Open Questions
- Should `AgentBuilder.quick_start()` include the minimal file toolset by default, or remain `noop`-only (recommended: remain minimal and require explicit `.with_tools(...)`)?
- Error surface: should failure `ToolResult.error` be structured codes only (e.g., `PATH_NOT_ALLOWED`) or human messages (or both)?

