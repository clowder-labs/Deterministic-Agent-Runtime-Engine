## ADDED Requirements
### Requirement: Session initialization applies effective config
The runtime SHALL resolve the effective configuration via ConfigProvider during session initialization and attach it to SessionContext before entering the Milestone Loop.

#### Scenario: Config available to runtime loops
- **WHEN** runtime.init() is called for a task
- **THEN** SessionContext carries the effective config snapshot so Plan/Execute/Tool loops and components can read consistent settings
