## 1. Edit-line default behavior
- [x] 1.1 Add a failing test proving `edit_line` insert succeeds when `line_number` is omitted.
- [x] 1.2 Update `edit_line` execution to default missing `line_number` to 1.

## 2. MCP timeout coercion hardening
- [x] 2.1 Add a failing test proving invalid MCP `timeout_seconds` does not crash and falls back.
- [x] 2.2 Update MCP timeout parsing to safely coerce and fallback on invalid/non-positive values.

## 3. Validation
- [x] 3.1 Run targeted pytest for affected modules.
- [x] 3.2 Run `openspec validate fix-p1-tool-input-defaults --strict`.
