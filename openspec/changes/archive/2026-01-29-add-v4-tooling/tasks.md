## 1. Implementation
- [x] 1.1 Add v4.0-aligned tool interfaces/types in `dare_framework3_4` (gateway, execution control, tool/provider contracts, risk enum, run context).
- [x] 1.2 Implement default tool runtime components (gateway/providers, MCP adapter stub, execution control, run-context state) and update exports.
- [x] 1.3 Implement trusted tool listings for `Context.listing_tools()` by converting `IToolGateway.list_capabilities()` into model tool defs.
- [x] 1.4 Port and adapt workspace file tools plus shared file utils (guardrails, workspace-root enforcement, deterministic search ordering).
- [x] 1.5 Ensure basic tools (`run_command`, `noop`) are present and compatible with the new tool types.
- [x] 1.6 Add unit tests for file tools (path enforcement, guardrails, deterministic search ordering, edit behavior).
- [x] 1.7 Update `examples/base_tool/README.md` to describe the built-in toolset and v4.0 configuration knobs.
- [x] 1.8 Validation: run relevant pytest targets for new/updated tests.
