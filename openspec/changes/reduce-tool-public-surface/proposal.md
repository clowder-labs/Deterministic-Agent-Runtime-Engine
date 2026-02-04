# Change: Reduce tool domain public surface

## Why
The tool domain currently re-exports many internal implementations via
`dare_framework.tool.__init__`, which expands the public API surface, increases
misuse risk, and makes future refactors harder. We want a minimal, stable
facade that exposes only kernel contracts, interfaces, and cross-domain types.

## What Changes
- Shrink `dare_framework.tool.__init__` to expose only stable kernel/interfaces
  and required shared types; remove direct re-exports of `_internal` classes.
- Move core tool contracts (`ITool`, `IToolProvider`) into `tool.kernel` to
  avoid forward references and make tool interfaces part of the stable kernel.
- Keep `ToolManager` as the supported default implementation (public), but move
  it to a dedicated module (e.g. `default_tool_manager.py`) instead of
  `_internal`.
- Keep built-in tools as defaults but **not** exposed in the main facade.
- Move `IExecutionControl` out of kernel into tool `interfaces` (tool control
  plane is optional, not core).
- Move execution-control exceptions into a dedicated `tool/exceptions.py`.
- Move MCP and Skill interfaces out of tool domain (MCP → `mcp`, Skill → `skill`),
  and integrate via `IToolProvider` implementations (e.g. `MCPToolProvider`,
  `SkillTool`).
- Add entrypoint-based provider loading in `ToolManager` (supports MCP tool
  provider discovery without hard-coding). Proposed entrypoint group:
  `dare_framework.tool_providers`.
- Update internal imports/tests/examples and docs to match the new surface.

## Impact
- **Breaking**: `from dare_framework.tool import ReadFileTool, ...` will no
  longer work (built-in tools are defaults but not public).
- **Potential breaking**: `IExecutionControl` import path changes
  (`tool.kernel` → `tool.interfaces`), and exceptions move to `tool.exceptions`.
- **Breaking**: MCP/Skill interfaces are no longer exported from tool domain.
- Affected docs: `docs/design/modules/tool/README.md`,
  `docs/design/Framework_MinSurface_Review.md`.
- Affected code: tool package facade, tests, examples, and MCP init.
