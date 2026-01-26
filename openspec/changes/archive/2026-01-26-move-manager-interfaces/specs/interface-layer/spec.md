## ADDED Requirements
### Requirement: Manager interfaces are domain-owned
The system SHALL define component manager interfaces alongside their owning domain interfaces, not in the config domain. Specifically:
- Tool manager: `dare_framework3_4/tool/interfaces.py`
- Model adapter manager: `dare_framework3_4/model/interfaces.py`
- Planner/validator/remediator managers: `dare_framework3_4/plan/interfaces.py`
- Hook manager: `dare_framework3_4/hook/interfaces.py`

The protocol adapter manager SHALL be defined at the package root in `dare_framework3_4/protocol_adapter_manager.py` until a dedicated protocol domain exists.

#### Scenario: Tool manager import path
- **WHEN** a contributor imports `IToolManager`
- **THEN** it is available from `dare_framework3_4.tool.interfaces` and not from `dare_framework3_4.config.interfaces`.

#### Scenario: Plan manager grouping
- **WHEN** a contributor looks for planner/validator/remediator managers
- **THEN** the manager interfaces are defined alongside `IPlanner`, `IValidator`, and `IRemediator` in the plan domain.

#### Scenario: Protocol adapter manager root
- **WHEN** a contributor imports `IProtocolAdapterManager`
- **THEN** it is available from `dare_framework3_4.protocol_adapter_manager`.
