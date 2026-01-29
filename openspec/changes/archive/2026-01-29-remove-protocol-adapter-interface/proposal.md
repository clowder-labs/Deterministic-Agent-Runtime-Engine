# Change: Remove protocol adapter interface

## Why
The protocol adapter layer is not needed yet and adds surface area without active integration. Removing it simplifies the public API and avoids maintaining unused abstractions.

## What Changes
- **BREAKING** Remove `IProtocolAdapter` and related adapter interfaces from the tool domain.
- **BREAKING** Remove `IProtocolAdapterManager` and any builder wiring for protocol adapters.
- Remove MCP adapter implementation and any deprecated providers tied to protocol adapters.
- Update docs/specs/examples/tests to reflect the removal.

## Impact
- Affected specs: `interface-layer`, `protocol-adapters`
- Affected code: `dare_framework/tool/interfaces.py`, `dare_framework/tool/__init__.py`, `dare_framework/tool/_internal/adapters/`, `dare_framework/protocol_adapter_manager.py`, builder wiring, docs/tests
