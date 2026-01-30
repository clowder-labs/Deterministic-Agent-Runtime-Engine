# Change: Update tool call identity to use ITool.name

## Why
LLM-facing tool names are currently UUID-based capability IDs, which are hard to read, remember, and debug. Users want stable, human-friendly tool identifiers that match `ITool.name` while keeping the internal registry safe and auditable.

## What Changes
- **BREAKING**: LLM-facing tool definitions use `function.name == ITool.name` instead of `capability_id`.
- Tool routing resolves tool calls by `ITool.name` and maps to the trusted `capability_id` before invocation.
- Tool names are required to be globally unique across the registry.
- `capability_id` remains the internal stable identity and is still exposed for observability.

## Impact
- Affected specs: `interface-layer`
- Affected code: tool manager tool-definition export, runtime tool-call routing, tool registry validation, tests, and examples.
