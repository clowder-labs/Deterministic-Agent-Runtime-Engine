# Change: Use tool name as capability id

## Why
Random UUID-based capability ids make logs hard to read and increase tool-call mismatches when models return tool names instead of ids. The framework already treats tool `name` as a stable identity; aligning capability ids with tool names simplifies routing and improves reliability.

## What Changes
- **BREAKING**: ToolManager will use `ITool.name` as the canonical `capability_id` instead of generating UUIDs.
- Tool registration will enforce unique tool names and fail fast on duplicates.
- Tool definitions exposed to the model will use `function.name == tool.name`.
- Update OpenSpec requirements to reflect name-based capability ids.
- Add/adjust unit tests to lock the new behavior.

## Impact
- Affected specs: `interface-layer`, `component-management`.
- Affected code: ToolManager registry and any callers that assume UUID capability ids.
- Migration: tooling that previously stored UUID capability ids must switch to tool names.
