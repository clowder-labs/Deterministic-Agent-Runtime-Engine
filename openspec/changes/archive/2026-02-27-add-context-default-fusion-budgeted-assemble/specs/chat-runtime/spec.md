## ADDED Requirements

### Requirement: Default context assembly fuses STM/LTM/Knowledge

The canonical default `Context.assemble()` path SHALL include retrieval results from LTM and Knowledge in addition to STM when sources are available.

#### Scenario: Assemble includes all available sources
- **GIVEN** STM has recent messages and both LTM and Knowledge are configured
- **WHEN** `Context.assemble()` is called
- **THEN** assembled messages include STM messages plus retrieved LTM and Knowledge messages
- **AND** retrieval metadata includes source counts and query text

### Requirement: Retrieval query derives from current user intent

The default assembly strategy SHALL derive retrieval query from the latest user-intent message in STM.

#### Scenario: Latest user message drives retrieval query
- **GIVEN** STM contains multiple turns including at least one user message
- **WHEN** `Context.assemble()` is called
- **THEN** LTM and Knowledge retrieval are invoked with the latest user message content as query

### Requirement: Budget-aware degradation for retrieval sources

The default assembly strategy SHALL degrade retrieval under low remaining token budget before model invocation.

#### Scenario: Low budget skips retrieval sources
- **GIVEN** remaining token budget is insufficient after reserving baseline STM and safety buffer
- **WHEN** `Context.assemble()` is called
- **THEN** LTM/Knowledge retrieval results are omitted
- **AND** metadata marks `degraded=true` with degradation reason

#### Scenario: Retrieval exceptions degrade source without failing assemble
- **GIVEN** one retrieval source raises an exception during get
- **WHEN** `Context.assemble()` is called
- **THEN** assemble still succeeds with available sources
- **AND** metadata records degraded source reason
