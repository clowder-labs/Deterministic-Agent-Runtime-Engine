## MODIFIED Requirements
### Requirement: Verification examples track canonical contracts
The canonical examples SHALL remain present and SHALL be updated to use the agent-domain builder API.

#### Scenario: Basic chat example imports agent builder
- **GIVEN** `examples/basic-chat/chat_simple.py`
- **WHEN** it is executed in a configured environment
- **THEN** it composes the agent using `BaseAgent` builder factories
