## Context
The protocol adapter surface (IProtocolAdapter/IProtocolAdapterManager) is currently unused in the runtime. Keeping it inflates the interface surface and suggests capabilities that do not exist in practice.

## Goals / Non-Goals
- Goals:
  - Remove the protocol adapter interfaces and related manager from the public API.
  - Delete the unused MCP adapter implementation and deprecated protocol adapter provider stubs.
- Non-Goals:
  - Replace protocol adapters with an alternative integration path.
  - Add new protocol discovery behavior.

## Decisions
- Decision: Remove `IProtocolAdapter` and `IProtocolAdapterManager` entirely.
- Decision: Remove the MCP adapter implementation and protocol adapter provider stub.

## Risks / Trade-offs
- **Breaking changes**: downstream code relying on these interfaces will need to migrate.
- **Future work**: reintroducing protocol adapters later will require a new proposal.

## Migration Plan
1. Remove interfaces, manager, and internal adapters/providers.
2. Update builder to drop protocol adapter wiring.
3. Update docs/specs/tests/examples to remove references.

## Open Questions
- None.
