## 1. Spec updates
- [x] 1.1 Update interface-layer requirements to remove protocol adapter interface surface.
- [x] 1.2 Update protocol-adapters spec to reflect removal or de-scope.

## 2. Code changes
- [x] 2.1 Remove `IProtocolAdapter` and `IProtocolAdapterManager` interfaces and exports.
- [x] 2.2 Remove MCP adapter implementation and deprecated protocol adapter provider.
- [x] 2.3 Update builder wiring and internal exports; keep design docs unchanged per request.

## 3. Validation
- [x] 3.1 Run `openspec validate remove-protocol-adapter-interface --strict`.
