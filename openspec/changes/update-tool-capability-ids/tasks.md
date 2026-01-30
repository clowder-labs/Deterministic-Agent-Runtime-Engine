## 1. Spec Updates
- [x] Update interface-layer spec to use tool name as capability id and describe routing behavior
- [x] Update component-management spec to enforce unique tool names instead of UUIDs

## 2. Code Updates
- [x] ToolManager uses tool name as capability id for register_tool and provider registration
- [x] ToolManager rejects duplicate tool names with a clear error
- [x] Ensure list_tool_defs and invoke paths align with name-based ids

## 3. Tests
- [x] Add a unit test asserting capability_id == tool.name
- [x] Add a unit test asserting duplicate names raise
- [x] Run targeted pytest for new/updated tests
