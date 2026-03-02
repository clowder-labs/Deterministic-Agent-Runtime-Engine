## ADDED Requirements

### Requirement: Tool pair safe compression
The runtime SHALL preserve tool invocation/result integrity during compression.  
When a compressed context retains an assistant tool call, it SHALL retain matching tool result messages for the retained call ids.

#### Scenario: Compression keeps tool call and result together
- **GIVEN** context messages include `assistant(tool_calls=[id=tc-1])` and `tool(name=tc-1)`
- **WHEN** compression is triggered
- **THEN** both messages are retained together, or both are removed together
- **AND** no orphan `tool` message remains without a matching retained tool call

### Requirement: Token-aware compression trigger
The runtime SHALL support token-aware compression decisions before model generation.

#### Scenario: Compression is triggered when token budget is near limit
- **GIVEN** current context token estimate is near/exceeds configured token threshold
- **WHEN** the execute loop is about to call the model
- **THEN** compression is triggered automatically before model invocation

### Requirement: Compression strategy observability metadata
Compressed messages SHALL include strategy metadata for downstream observability.

#### Scenario: Compressed summary carries strategy marker
- **WHEN** runtime applies summary or pair-safe compression
- **THEN** compressed system message metadata includes a stable strategy identifier
