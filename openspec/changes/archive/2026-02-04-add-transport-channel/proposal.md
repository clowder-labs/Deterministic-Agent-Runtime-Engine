# Change: Add transport channel domain for agent↔client interaction

## Why
当前缺少统一的 transport domain 来承载 Agent 与外部 client 的交互协议，导致接入层与编排层耦合、回压语义不一致、以及 hook 输出路径不清晰。

## What Changes
- Add a new transport capability that defines `ClientChannel`, `AgentChannel`, and `TransportEnvelope` contracts.
- Provide a deterministic queue + pump model with blocking backpressure and stack-penetration avoidance.
- Define minimal lifecycle rules (`start` idempotent, `stop` drop outgoing messages) and error handling (receiver/sender errors are logged and non-fatal).
- Clarify streaming envelope fields and interrupt semantics for MVP.
- Update transport design docs to align naming/semantics, archive redundant drafts, and refresh `docs/design/Architecture.md` + module index.
- Sync agent integration and examples with the transport channel contracts and envelope usage.

## Impact
- Affected specs: `transport-channel` (new)
- Affected code: new `dare_framework/transport` domain; agent integration to send/poll via `AgentChannel`; hook-to-client outputs route through transport.
- Affected docs: `docs/design/module_design/transport/transport_mvp.md`, `docs/design/Architecture.md`, `docs/design/module_design/README.md` (plus archiving redundant drafts).
- Affected examples: `examples/*` that expose agent↔client interaction.
