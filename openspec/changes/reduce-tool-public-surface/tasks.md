## 1. Implementation
- [x] 1.1 Update tool package facade to expose only kernel/interfaces/types.
- [x] 1.2 Add supported default ToolManager module (e.g. `default_tool_manager.py`).
- [x] 1.3 Move `IExecutionControl` to `tool.interfaces` and update imports.
- [x] 1.4 Add `tool/exceptions.py` and migrate execution-control exceptions.
- [x] 1.5 Move MCP/Skill interfaces to their domains; add MCPToolProvider and SkillTool integration.
- [x] 1.6 Add entrypoint-based provider discovery in ToolManager.
- [x] 1.7 Update internal imports/tests/examples for new surface.
- [x] 1.8 Update tool module design doc to document minimal public surface.

## 2. Specs
- [x] 2.1 Update package-facades spec to require minimal public surface for tool domain.
