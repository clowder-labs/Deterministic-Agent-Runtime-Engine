# define-core-models Specification

## Purpose
TBD - created by archiving change refactor-layered-structure. Update Purpose after archive.
## Requirements
### Requirement: Model Partitioning
Core data models SHALL be defined per domain in `dare_framework3_3/<domain>/types.py` and re-exported from the corresponding domain package. A global `dare_framework3_3.types` facade SHALL NOT be required.

#### Scenario: Locating a data model
- **WHEN** a contributor needs `ToolDefinition`
- **THEN** it is defined under `dare_framework3_3/tool/types.py` and re-exported from `dare_framework3_3.tool`.

### Requirement: Plan Model Staging
The framework SHALL keep proposed and validated plan step models distinct, without aliasing proposal models as validated models.

#### Scenario: Distinguishing plan stages
- **WHEN** a contributor reads the plan models
- **THEN** proposed steps and validated steps are represented by separate types with explicit names in `dare_framework3_3/plan/types.py`.

