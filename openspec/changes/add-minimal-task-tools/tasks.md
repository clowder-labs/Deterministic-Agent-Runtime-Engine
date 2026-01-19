## 1. Implementation
- [x] 1.1 Add `read_file`, `search_code`, `write_file`, `edit_line` under `dare_framework2/tool/impl/` with shared path/guardrail utilities.
- [x] 1.2 Enforce workspace-root boundaries using `Config.workspace_roots` when present; default to `Path.cwd()` when absent.
- [x] 1.3 Apply guardrails from `Config.tools.<tool_name>` with safe defaults; ensure `search_code` ordering is deterministic.
- [x] 1.4 Emit `Evidence` records for successful operations (read/search/write/edit).
- [x] 1.5 Wire config into `dare_framework2` tool contexts (extend `RunContextState` and set it from `AgentBuilder`).
- [x] 1.6 Add unit tests covering path enforcement, size limits, deterministic search ordering, and strict delete mismatch.
- [x] 1.7 Run `pytest` for relevant test subsets and ensure OpenSpec validation passes.
