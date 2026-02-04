Tool Internal Layout (dare_framework)

This directory contains non-public implementations for the tool domain.
Imports should prefer `dare_framework.tool` or `dare_framework.tool._internal`
aggregates; the subpackages below organize internal responsibilities.

Subpackages
- control: execution control plane (pause/resume/checkpoints).
- tools: built-in tools shipped with the framework.

Top-level internal modules
- native_tool_provider.py: provider that returns built-in tools.
- file_utils.py: shared file/path helpers.

Notes
- `ToolManager` implementation lives in `dare_framework/tool/default_tool_manager.py`
  and is re-exported by `dare_framework.tool._internal`.

Manager vs built-in tools
- Manager-style components live at the top level (native_tool_provider).
- System/built-in tools live in `tools/` (file/command helpers, noop/echo).

Naming
- Use snake_case for file and function names.
- Keep new internal modules flat unless they are part of `control/` or `tools/`.
- Re-export through `dare_framework.tool._internal.__init__` when needed.
