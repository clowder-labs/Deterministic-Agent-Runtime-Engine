# Change: Realign interaction flow around channel kind-dispatch

## Why
当前实现已经部分重构，但与讨论达成的一致方案仍有偏差，主要体现在职责边界不稳定：
- `ActionHandlerDispatcher` 一度同时处理 message/action/control，造成语义膨胀。
- 分流逻辑在 channel、dispatcher、agent loop 之间来回迁移，导致实现与设计文档不一致。
- builder 注入与运行时兜底策略不清晰，容易出现“改了 agent 字段名就影响 transport”的耦合问题。

本提案目标是先冻结一版可执行的设计边界，再按文档实施，避免继续漂移。

## What Changes
本次提案明确以下最终目标（以此为后续代码修改唯一依据）：

1. `TransportEnvelope.kind` 使用强类型 `EnvelopeKind`（`MESSAGE|ACTION|CONTROL`）。
2. `DefaultAgentChannel` 按 `EnvelopeKind` 进行分流：
   - `MESSAGE`：入 inbox，由 agent loop 消费。
   - `ACTION`：直接交给 `ActionHandlerDispatcher`。
   - `CONTROL`：直接交给 `AgentControlHandler`。
3. `ActionHandlerDispatcher` 只负责 `ResourceAction -> IActionHandler` 路由，不处理 control/message。
4. `AgentControlHandler` 只负责 `AgentControl -> agent method` 映射。
5. builder 在 `build()` 阶段完成 handler 组装与注入（action + control），agent loop 只处理 prompt 类 message。
6. slash 解析放在 client adapter（如 stdio）侧完成，transport 内部不再基于 message 文本推断 action。
7. 会话处理保持串行（不引入并发模型），但对 action 执行增加统一超时与错误码。
8. 统一 action/control/message 的响应结构为 `kind + target + ok + resp`，确保与 `TransportEnvelope` 对应。
9. 明确入口规范：stdio 可做 slash 适配；websocket/A2A 必须直接发送结构化 envelope。
10. 增加动作发现能力：客户端输入单个 `/` 时触发查询，返回当前已注册 actions 列表。

## Before / After (scope baseline)

### Before
- 分流职责分散，可能在 dispatcher 或 agent loop 中解析 control/action。
- `ActionHandlerDispatcher` 可能包含 control 路由逻辑。
- `MESSAGE` 以外 envelope 可能进入 agent loop 再二次判断。

### After
- 分流入口唯一：`DefaultAgentChannel._enqueue_inbox`。
- `ActionHandlerDispatcher` 单一职责：只处理 `ACTION`。
- `AgentControlHandler` 单一职责：只处理 `CONTROL`。
- agent loop 只消费 `MESSAGE`（`str|Task` prompt 路径）。
- builder 注入是启动前置条件；`BaseAgent.start()` 不再做 handler 兜底注入，缺失则 fail-fast。

## Non-Goals
- 不新增新的 action 资源域（仍限定 `config/tools/mcp/skills/model`）。
- 不调整 security boundary 的 action 参数语义（后续单独提案）。
- 不引入 stop/close 作为 runtime control；生命周期由 host/client 直接调用 `agent.stop()`。

## Impact
- Affected specs:
  - `transport-channel`（明确 channel 分流职责与 `EnvelopeKind`）
  - `interaction-dispatch`（明确 dispatcher/control handler 的单一职责）
- Affected code (implementation stage):
  - `dare_framework/transport/types.py`
  - `dare_framework/transport/_internal/default_channel.py`
  - `dare_framework/transport/interaction/dispatcher.py`
  - `dare_framework/transport/interaction/control_handler.py`
  - `dare_framework/agent/base_agent.py`
  - `dare_framework/agent/builder.py`
  - `dare_framework/transport/_internal/adapters.py`
  - `tests/unit/test_transport_channel.py`
  - `tests/unit/test_interaction_dispatcher.py`

## Breaking / Compatibility
- `TransportEnvelope.type` 已移除，不做兼容回退。
- 不保留 “message 文本以 `/` 开头由 dispatcher 自动识别 action” 的隐式兼容。
- `/quit`/`/exit` 仍作为 client 侧生命周期行为，不进 transport control。
