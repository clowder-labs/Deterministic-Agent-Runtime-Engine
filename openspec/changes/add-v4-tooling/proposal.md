# Change: Add v4 tool runtime + workspace file tools (dare_framework3_4)

## Why
The v4.0 base (`dare_framework3_4`) currently exposes only a thin `IToolProvider` stub and is missing the tool runtime interfaces/types and default implementations described in `doc/design/Interfaces_v4.0.md`. The minimal workspace file toolset (read/search/write/edit) exists only in commit `a1d8ad5c6` on branch `add_tools`, and the project lacks a v4.0-aligned implementation inside `dare_framework3_4`. To support deterministic task execution and align with the v4.0 design requirements, we need to port and adapt those tool implementations to `dare_framework3_4`, using the v4.0 config shape and trusted registry flow.

## What Changes
- Add v4.0-aligned tool interfaces/types (IToolGateway/IExecutionControl/ITool/ICapabilityProvider/etc.) and risk enums inside `dare_framework3_4`.
- Implement default tool runtime pieces (gateway/providers, MCP adapter stubs, execution control, run-context state) and a tool provider that converts trusted capabilities into model tool definitions.
- Port the minimal workspace file tools (`read_file`, `search_code`, `write_file`, `edit_line`) with guardrails and workspace-root enforcement, adapted to the v4.0 config shape.
- Ensure basic tools (`run_command`, `noop`) are present and compatible with the new tool types.
- Add unit tests for file tools and deterministic search ordering; update docs to reflect the built-in toolset and configuration knobs.

## Impact
- Affected specs: `interface-layer` (new requirement for trusted tool listings), `workspace-file-tools` (new capability), `tool-local-command` (implementation).
- Affected code: `dare_framework3_4/tool/*`, `dare_framework3_4/security/*` (risk types), tests, docs.
