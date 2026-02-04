# Module: event

> Status: interface-only (2026-01-31). TODO indicates missing implementation and integration.

## 1. 定位与职责

- 提供 WORM 事件日志接口，支持审计、查询与重放。
- 作为“事实来源”，支持任务复验与外部审计系统。

## 2. 关键概念与数据结构

- `Event`：事件记录（event_type/payload/timestamp/hash）。
- `RuntimeSnapshot`：基于 event log 的重放快照。

## 3. 关键接口

- `IEventLog.append(...)`：追加事件。
- `IEventLog.query(...)`：查询事件。
- `IEventLog.replay(...)`：按 event_id 重放。
- `IEventLog.verify_chain()`：哈希链校验。

## 4. 与其他模块的交互

- **Agent**：DareAgent 可选记录 session/plan/tool/model 事件。
- **HITL**：未来可记录 pause/wait/resume 事件链。

## 5. 现状与限制

- 当前仅有接口与类型，缺少默认实现。
- 另有 `dare_framework/events/*` 旧 event bus 实现（legacy），未与新架构对齐。

## 6. TODO / 未决问题

- TODO: 提供默认 EventLog 实现（持久化 + hash-chain）。
- TODO: 统一 legacy event bus 与 WORM event log 的关系。
- TODO: 定义稳定事件 taxonomy 与 payload schema。

## 7. Design Clarifications (2026-02-03)

- Doc/Impl gap: `dare_framework/events/*` (legacy) coexists with `event` domain; needs migration policy.
- Doc gap: event taxonomy/schema must be defined for cross-module payloads.
