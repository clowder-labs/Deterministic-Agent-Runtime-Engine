# Change: Fix P1 tool input defaults and metadata coercion

## Why
Two P1 issues caused avoidable tool failures:
- `edit_line` rejected insert calls when `line_number` was omitted even though the schema declares a default.
- MCP tool metadata with non-numeric `timeout_seconds` raised conversion errors and could break capability registration paths.

## What Changes
- Ensure `edit_line` treats missing `line_number` as line 1 for insert/delete indexing.
- Ensure MCP tool timeout parsing is defensive: invalid or non-positive timeout values fall back to a safe default.
- Add regression tests for both behaviors.

## Impact
- Affected specs: `workspace-file-tools`, `component-management`
- Affected code:
  - `dare_framework/tool/_internal/tools/edit_line.py`
  - `dare_framework/mcp/tool_provider.py`
  - `tests/unit/test_v4_file_tools.py`
  - `tests/unit/test_mcp_tool_provider.py`
