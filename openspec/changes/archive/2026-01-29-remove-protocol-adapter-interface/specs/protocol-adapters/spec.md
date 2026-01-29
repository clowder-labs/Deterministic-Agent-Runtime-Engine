## ADDED Requirements
### Requirement: Protocol adapter surface is deferred
The framework SHALL NOT expose protocol adapter interfaces until a dedicated integration is specified.

#### Scenario: Protocol adapters are not available
- **WHEN** a contributor looks for protocol adapter contracts
- **THEN** only local tool/provider surfaces are available

## REMOVED Requirements
### Requirement: Protocol Adapter Contract
**Reason**: Protocol adapter interfaces are removed from the current runtime surface.
**Migration**: Reintroduce with a dedicated proposal when protocol integration is required.

#### Scenario: Adapter discovers capabilities
- **WHEN** `IProtocolAdapter.discover()` is invoked
- **THEN** it returns canonical `CapabilityDescriptor` items tagged with `CapabilityType`

### Requirement: MCP Adapter Integration Path
**Reason**: MCP adapter implementation is removed alongside protocol adapter interfaces.
**Migration**: Reintroduce with a dedicated proposal when protocol integration is required.

#### Scenario: MCP is configured
- **WHEN** an MCP adapter is configured and connected
- **THEN** discovered tool capabilities are invokable via `IToolGateway.invoke()` using canonical capability ids

### Requirement: Protocol Adapters Are Optional
**Reason**: Protocol adapter surface is removed; optionality is no longer applicable.
**Migration**: Reintroduce with a dedicated proposal when protocol integration is required.

#### Scenario: No protocol adapters configured
- **WHEN** no protocol adapters are provided
- **THEN** capability listing and invocation still work for native tools/providers
