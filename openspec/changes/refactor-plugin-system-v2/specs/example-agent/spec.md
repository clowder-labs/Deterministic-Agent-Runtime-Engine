## MODIFIED Requirements

### Requirement: Verification examples track v2 contracts
The coding-agent verification examples SHALL remain present and SHALL be updated to use the v2 contracts and plugin system.

#### Scenario: Real-model coding agent example imports v2 builder/contracts
- **GIVEN** `examples/coding-agent/real_model_agent.py`
- **WHEN** it is executed in a configured environment
- **THEN** it composes the agent using v2 builder + v2 plugin loading (and does not depend on removed v1 runtime interfaces)
