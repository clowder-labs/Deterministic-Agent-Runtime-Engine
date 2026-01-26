## 1. Implementation
- [x] 1.1 Add a minimal `dare_framework/builder/` package with `AgentBuilder` that composes `SimpleChatAgent`, context, budget, and tool wiring.
- [x] 1.2 Add a default `IToolGateway` implementation under `dare_framework/tool/_internal/` that aggregates `ICapabilityProvider`s and enforces envelope allowlists on invoke.
- [x] 1.3 Add a gateway-backed `IToolProvider` that derives tool definitions from `IToolGateway.list_capabilities()` for Context assembly.
- [x] 1.4 Add a native in-process capability provider that adapts local `ITool` instances into `CapabilityDescriptor`s with optional metadata extraction.
- [x] 1.5 Wire builder defaults to register native tools/providers into the default gateway and pass the gateway-backed tool provider into `SimpleChatAgent`.
- [x] 1.6 Add unit tests for builder composition, tool gateway aggregation/allowlist enforcement, and tool definition derivation.

## 2. Validation
- [x] 2.1 Run targeted unit tests for the new builder/tool gateway behavior.
- [x] 2.2 Run `python -c "import dare_framework"` to ensure the canonical package still imports cleanly.
