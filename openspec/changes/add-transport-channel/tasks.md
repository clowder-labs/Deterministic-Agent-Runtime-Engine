## 1. Implementation
- [x] 1.1 Define transport domain contracts (`types.py`, `kernel.py`, `interfaces.py`) with `ClientChannel`, `AgentChannel`, `TransportEnvelope`.
- [x] 1.2 Implement default `AgentChannel` queue + pump model (inbox/outbox, blocking backpressure, start/stop semantics).
- [x] 1.3 Add minimal client adapters (stdio/direct/websocket placeholders) that implement `ClientChannel` or document integration points.
- [x] 1.4 Integrate Agent loop to use `AgentChannel.poll/send` for external interaction (hooks output uses transport).
- [x] 1.5 Add tests for backpressure, start/stop idempotency, interrupt cancellation, and receiver error swallowing.
- [x] 1.6 Update transport design doc (`docs/design/modules/transport/transport_mvp.md`) to reflect channel contracts, lifecycle, error handling, and usage examples.
- [x] 1.7 Archive redundant transport design docs and update `docs/design/Architecture.md` + `docs/design/modules/README.md` references.
- [x] 1.8 Update examples to use `AgentChannel`/`TransportEnvelope` contracts and the new integration flow.
