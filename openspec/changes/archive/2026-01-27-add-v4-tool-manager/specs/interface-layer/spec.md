## ADDED Requirements
### Requirement: Tool manager contract
The interface layer SHALL define an `IToolManager` contract in the tool domain. The contract SHALL support trusted tool registration, provider aggregation, and prompt tool definition export without executing tools. At minimum it MUST include:
- `register_tool(...)`, `unregister_tool(...)`, `update_tool(...)`
- `register_provider(...)`, `unregister_provider(...)`
- `list_capabilities(...)`, `refresh(...)`
- `list_tool_defs(...)`, `get_capability(...)`
- `health_check(...)`

#### Scenario: Register tool returns a capability descriptor
- **GIVEN** a valid `ITool` implementation
- **WHEN** `register_tool(...)` is called
- **THEN** the manager returns a `CapabilityDescriptor` with a stable `capability_id` and trusted metadata

#### Scenario: Tool definitions are derived from registry
- **GIVEN** a tool has been registered into the manager
- **WHEN** `list_tool_defs()` is called
- **THEN** the result is derived from the manager registry and not from model output

## MODIFIED Requirements
### Requirement: Manager interfaces are domain-owned
The system SHALL define component manager interfaces alongside their owning domain interfaces, not in the config domain. Specifically:
- Tool manager: `dare_framework/tool/interfaces.py`
- Model adapter manager: `dare_framework/model/interfaces.py`
- Planner/validator/remediator managers: `dare_framework/plan/interfaces.py`
- Hook manager: `dare_framework/hook/interfaces.py`

The protocol adapter manager SHALL be defined at the package root in `dare_framework/protocol_adapter_manager.py` until a dedicated protocol domain exists.

#### Scenario: Tool manager import path
- **WHEN** a contributor imports `IToolManager`
- **THEN** it is available from `dare_framework.tool.interfaces` and not from `dare_framework.config.interfaces`.

#### Scenario: Plan manager grouping
- **WHEN** a contributor looks for planner/validator/remediator managers
- **THEN** the manager interfaces are defined alongside `IPlanner`, `IValidator`, and `IRemediator` in the plan domain.

#### Scenario: Protocol adapter manager root
- **WHEN** a contributor imports `IProtocolAdapterManager`
- **THEN** it is available from `dare_framework.protocol_adapter_manager`.
