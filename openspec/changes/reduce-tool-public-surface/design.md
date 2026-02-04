## Context
- Current tool facade exports many internal implementations and helpers.
- We want a minimal surface that limits public API to stable contracts.

## Decisions
- `dare_framework.tool` exposes kernel interfaces, pluggable interfaces,
  required shared types, and the supported default `ToolManager`.
- `ITool` and `IToolProvider` are core contracts and live in `tool.kernel`
  (no string forward refs inside kernel).
- `ToolManager` remains a **supported default implementation**, but lives in a
  dedicated module (e.g. `default_tool_manager.py`) rather than `_internal`.
- Built-in tools are defaults but are not exported in the main facade.
- `IExecutionControl` is moved from kernel to tool interfaces (still inside the
  tool domain, but not part of the kernel contract).
- Execution-control exceptions move to `tool/exceptions.py`.
- MCP + Skill interfaces are owned by their domains; integration occurs via
  `IToolProvider` implementations (e.g. `MCPToolProvider`, `SkillTool`).
- Tool providers can be discovered via Python entry points.
  Group name: `dare_framework.tool_providers`.
  `ToolManager` will load and instantiate providers from entry points in
  addition to those passed explicitly.

## Non-Goals
- No behavioral changes to tool execution.
- No refactor of tool registry logic beyond exports.

## Migration Plan
- Replace imports in repo from `dare_framework.tool` to internal/default paths
  for built-in tools (or load via `ToolManager`).
- Update docs to reflect the new import paths.
- Adjust `IExecutionControl` imports to `dare_framework.tool.interfaces`.
