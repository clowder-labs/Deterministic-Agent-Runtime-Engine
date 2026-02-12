# Design POC: Channel-first kind dispatch with strict handler boundaries

## Context
本 POC 文档用于冻结“特性流程修改”的目标实现，避免继续在实现期漂移。本文档不是代码现状描述，而是后续实现必须遵守的设计基线。

## Terminology
- 当前执行操作（previously called in-flight）: 指“当前正在执行、且可被 interrupt 取消”的单个运行任务。
- 本方案不引入并发输入处理：单个 agent 会话同一时刻仅处理一个用户输入。

## Goals
- `AgentChannel` 作为唯一入站分流入口，基于 `EnvelopeKind` 执行路由。
- `ActionHandlerDispatcher` 只负责 action，不处理 message/control。
- `AgentControlHandler` 只负责 control，不处理 action/message。
- `BaseAgent` 运行循环只消费 `MESSAGE`（prompt/Task）。
- builder 在 `build()` 阶段完成 handler 组装和注入。

## Non-Goals
- 不在本轮改动 `ISecurityBoundary` 参数模型。
- 不在本轮定义 stop/close 控制信号。
- 不做兼容旧的 `TransportEnvelope.type` 或隐式 slash 推断。

## Architecture Decisions (final)

### Decision 1: `EnvelopeKind` is the routing key
- `TransportEnvelope.kind` 使用强类型枚举：`MESSAGE|ACTION|CONTROL`。
- 路由优先级只看 `kind`，不再通过 message 文本推断交互类型。

### Decision 2: Channel owns inbound dispatch
- `DefaultAgentChannel._enqueue_inbox` 按 kind 分流：
  - `MESSAGE` -> `inbox.put(...)`
  - `ACTION` -> `ActionHandlerDispatcher.handle_action(...)`
  - `CONTROL` -> `AgentControlHandler.invoke(...)`
- Channel 对 action/control 路径负责回包错误响应（`reply_to=request.id`）。
- 输入处理模型为串行：同一会话按到达顺序逐条处理，不做 action/control 并发执行。

### Decision 3: Dispatcher and control handler are separated
- `ActionHandlerDispatcher`: `dict[ResourceAction, IActionHandler]` 注册与分发。
- `AgentControlHandler`: 持有强类型 agent 目标（`interrupt/pause/retry/reverse`）。
- 二者不互相依赖，不共享注册表。

### Decision 4: Builder-time composition
- `AgentBuilder.build()` 时根据现有 manager 组装 domain action handlers：
  - `config`, `tools`, `mcp`, `skills`, `model`
- 并将 `ActionHandlerDispatcher` + `AgentControlHandler` 注入 channel。
- `BaseAgent.start()` 不做兜底注入；若 channel 缺少 action/control handler 绑定，启动直接失败（配置错误）。

### Decision 5: Action timeout (no concurrency)
- 由于单会话串行处理，本轮不设计并发模型。
- 对 `ACTION` 处理增加超时约束（例如 `asyncio.wait_for`）：
  - 默认超时：30s（可配置）
  - 超时结果：返回统一 error 响应（`code="ACTION_TIMEOUT"`）

### Decision 6: Client-side slash adaptation
- stdio 等简单 client 负责把 slash 输入映射成结构化 envelope：
  - `/tools:list` -> `kind=ACTION, payload="tools:list"`
  - `/interrupt` -> `kind=CONTROL, payload="interrupt"`
  - `/` -> `kind=ACTION, payload="actions:list"`（查询当前注册动作）
- `/quit` `/exit` 为 client 生命周期命令，不进入 transport。

### Decision 7: Entry input contract
- `stdio`：允许 slash 适配，负责把输入规范化为结构化 envelope。
- `websocket` / `A2A`：必须直接发送结构化 envelope（显式 `kind` + `payload`），不依赖 slash 文本推断。
- 若发送 `kind=MESSAGE`，则一律按 prompt 处理，不再二次推断 action/control。

## Flow POC (before vs after)

### Before (problematic)
1. client sends envelope
2. agent loop polls all kinds
3. agent/dispatcher 内部再判断 message/action/control
4. control/action 逻辑可能与 prompt 执行耦合

### After (target)
1. client sends envelope with strong `kind`
2. channel `_enqueue_inbox` routes by `EnvelopeKind`
3. only `MESSAGE` enters agent inbox
4. action/control path is handled immediately by dedicated handlers
5. agent loop only executes prompt flow

## Runtime Sequence (target)

### Message
1. inbound `MESSAGE`
2. channel -> inbox
3. agent loop `poll()`
4. agent `run(prompt|Task)`

### Action
1. inbound `ACTION` with `resource:action`
2. channel -> `ActionHandlerDispatcher.handle_action`
3. dispatcher resolves `ResourceAction` -> `IActionHandler`
4. send `action_result` or `error` with `reply_to`

### Control
1. inbound `CONTROL` with `AgentControl`
2. channel -> `AgentControlHandler.invoke`
3. handler maps to agent method (`interrupt/pause/retry/reverse`)
4. send `control_result` or `error` with `reply_to`

## Unified response schema (target)
- 所有 handler 路径返回 `TransportEnvelope(kind=MESSAGE, reply_to=<request.id>)`。
- `payload` 使用统一结构：
  - success: `{"kind":"action|control|message","target":"<enum-or-message>","ok":true,"resp":{...}}`
  - failure: `{"kind":"action|control|message","target":"<enum-or-message>","ok":false,"resp":{"code":"<ERROR_CODE>","reason":"<human-readable>"}}`
- `message` 相关错误（如入队失败）若无法回包，必须记录日志与可观测事件。
- 未注册 action 或不支持的 action 必须返回 `resp.code="UNSUPPORTED_OPERATION"`。

## Contracts (target interfaces)
- `TransportEnvelope.kind: EnvelopeKind`
- `AgentChannel` adds:
  - `add_action_handler_dispatcher(...)`
  - `add_agent_control_handler(...)`
  - getter counterparts
- `ActionHandlerDispatcher`:
  - `register_action_handler(...)`
  - `handle_action(...)`
- `AgentControlHandler`:
  - `invoke(control, params)`

## Risks and Mitigations
- Risk: builder 未注入导致 action/control 无法处理  
  Mitigation: `BaseAgent.start()` 启动前做强校验，缺失直接失败并报配置错误。
- Risk: client 未按 kind 发送结构化 envelope  
  Mitigation: adapter 层统一规范，channel 返回结构化 error。
- Risk: action id 漂移  
  Mitigation: 所有注册与分发仅接受 `ResourceAction` 枚举。

## Acceptance Criteria
- channel 单元测试证明按 kind 分流（message 入队、action/control 不入队）。
- dispatcher 单元测试只覆盖 action 路由，不包含 control 路由。
- base agent 单元/集成测试证明 agent loop 仅处理 message。
- openspec validation 全量通过。
