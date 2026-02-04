## Context
- 需要一个独立的 transport domain 统一 Agent 与 Client 的交互语义。
- 目标是最小可落地（MVP），避免协议/网络层复杂度。
- 现有文档以 `transport_mvp.md` 为主，但在命名、生命周期、错误处理与消息约束上尚不完整。

## Goals / Non-Goals
- Goals:
  - 定义稳定的 transport contracts：`ClientChannel`, `AgentChannel`, `TransportEnvelope`。
  - 统一阻塞式回压与队列泵模型，避免栈穿透。
  - 最小生命周期：`start()` 幂等，`stop()` 可丢弃待发送消息。
  - 允许 hook 产生的对外消息通过 `AgentChannel.send(...)` 发送。
  - 更新传输设计文档与架构索引，并归档冗余草案文档。
  - 同步 agent 与 examples 对 transport channel 的使用方式。
- Non-Goals:
  - 不定义网络协议或编码细节。
  - 不在 MVP 中处理复杂的流式合并/优先级/丢弃策略。
  - 不引入 EventLog 或审计逻辑。

## Decisions
- Naming:
  - Use `ClientChannel` for the external adapter (sender/receiver attachment).
  - Use `AgentChannel` for the agent-facing interface (poll/send/run_interruptible/start/stop).
  - Use `TransportEnvelope` for the message container (distinct from `context.Message`).
- Factory:
  - Provide `AgentChannel.build(client_channel, *, max_inbox, max_outbox)` as the minimal construction entry.
- Agent integration:
  - `AgentChannel` is owned by the agent; `start()` spawns the internal poll loop that calls `run(...)` (no standalone loop helper).
- Codec:
  - Allow optional encoder/decoder injection in `AgentChannel.build(...)` for envelope transforms at the boundary.
- Backpressure:
  - Default blocking queues for inbox/outbox with max sizes; no drop/merge in MVP.
- Error handling:
  - Exceptions in sender/receiver are swallowed and logged; pumps continue.
- Interrupt:
  - `TransportEnvelope(kind="control", type="interrupt")` is the canonical envelope.
  - Interrupt handling is performed by agent loop; transport does not preempt by default.
- Streaming:
  - `stream_id` + `seq` optional; if present, `seq` is monotonically increasing per stream.
  - Ordering is preserved by single queue; no reordering guarantees beyond queue ordering.
- Documentation:
  - `docs/design/module_design/transport/transport_mvp.md` is the canonical transport design doc.
  - Archive `docs/design/module_design/transport/Transport_Domain_Design.md`, `InteractionStreaming.md`, and `Interaction_Design_Discussion.md`.
  - Update `docs/design/Architecture.md` and `docs/design/module_design/README.md` to reference the canonical doc.

## Alternatives considered
- Reusing `context.Message` as transport payload: rejected to avoid conflating conversational content with transport control signals.
- Naming using `ClientTransport/AgentTransport`: rejected due to role ambiguity; `ClientChannel`/`AgentChannel` is more explicit.

## Risks / Trade-offs
- Simplicity vs control: default blocking backpressure may stall in high-throughput streaming; deferred to non-MVP extensions.
- Swallowing receiver errors may hide issues; requires explicit logging hooks.

## Migration Plan
- Phase 1: Introduce transport domain contracts + default implementation.
- Phase 2: Integrate Agent to use `AgentChannel` for send/poll.
- Phase 3: Update client adapters (stdio/websocket/direct) to implement `ClientChannel`.
- Phase 4: Update/cleanup design docs + architecture index.

## Open Questions
- 是否需要将 Transport 与 EventLog/Hooks 的关系正式纳入审计链？（暂时不做）
- 是否需要配置层统一 `max_inbox/max_outbox` 的默认值？
