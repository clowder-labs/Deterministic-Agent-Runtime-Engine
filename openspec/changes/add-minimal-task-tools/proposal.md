# Change: Add minimal workspace file tools (framework2)

## Why
`dare_framework2` currently ships only a minimal tool surface (e.g., `noop`, `run_command`). The `add_tools` branch adds a stable workspace file toolset, but it targets `dare_framework/`. We need the same capability implemented in `dare_framework2/` to match the v2 architecture and allow real coding/task workflows.

## What Changes
- Port the minimal workspace file toolset to `dare_framework2`:
  - `read_file`, `search_code`, `write_file`, `edit_line`
- Enforce workspace-root boundaries and deterministic behavior (ordered traversal, bounded outputs).
- Support guardrails via `Config.tools.<tool_name>` with safe defaults and `Config.workspace_roots` for path scope.
- Ensure `dare_framework2` tool execution contexts can carry effective config so tools can read guardrails.
- Add unit tests for boundary enforcement, limits, determinism, and error handling.

## Impact
- Affected specs: `workspace-file-tools` (new); references `tool-local-command` for `workspace_roots`.
- Affected code: `dare_framework2/tool/impl/*`, `dare_framework2/tool/impl/run_context_state.py`, `dare_framework2/builder/builder.py`, unit tests under `tests/`.

## Notes / Assumptions
- Source of truth for behavior is the latest `add_tools` commit (`a1d8ad5`) but the implementation will follow `dare_framework2` patterns (protocols, types, tool gateway).
- Tools will be exposed as capabilities with IDs `tool:<name>` when using `NativeToolProvider`.

