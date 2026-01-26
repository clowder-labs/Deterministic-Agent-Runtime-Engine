# protocol-adapters Specification

## Purpose
TBD - created by archiving the prior kernel-architecture change. Update Purpose after archive.
## Requirements
### Requirement: Protocol Adapter Contract
The framework SHALL define `IProtocolAdapter` as the Layer 1 contract, responsible for translating protocol discovery/invocation to canonical `CapabilityDescriptor` shapes without leaking protocol details into the Kernel.

#### Scenario: Adapter discovers capabilities
- **WHEN** `IProtocolAdapter.discover()` is invoked
- **THEN** it returns canonical `CapabilityDescriptor` items tagged with `CapabilityType`

### Requirement: MCP Adapter Integration Path
The framework SHALL provide an initial MCP adapter integration path where discovered MCP tools can be registered into the Kernel via capability providers and invoked through `IToolGateway`.

#### Scenario: MCP is configured
- **WHEN** an MCP adapter is configured and connected
- **THEN** discovered tool capabilities are invokable via `IToolGateway.invoke()` using canonical capability ids

### Requirement: Protocol Adapters Are Optional
The Kernel SHALL remain functional when no protocol adapters are configured (native/local tools only).

#### Scenario: No protocol adapters configured
- **WHEN** no protocol adapters are provided
- **THEN** capability listing and invocation still work for native tools/providers
