# 运行期交互与 Streaming API 设计草案

> 状态：草案（用于讨论）
>
> 本文目标：把“运行期与用户交互”从编排逻辑中解耦出来，形成一套统一的 streaming API，使他人基于该 API 构建 CLI/Web/SDK 等不同形态的交互层。
>
> 约束：本文**不讨论渲染**（如何展示给人类），只讨论协议、流程与接口抽象。

---

## 1. 背景：为什么引入运行期交互会“别扭”

当用户只有“最开始的一次输入”，后续只旁路观察（hooks/日志），编排天然是线性函数：

`run(task) -> result`

引入运行期交互后，外部输入通常分为两类，语义完全不同：

1) **普通消息（non-interrupting）**：用户主动发消息，但不要求立刻打断当前动作  
   - 期望行为：缓存到 inbox，下一次编排需要输入时再消费。

2) **中断/控制（interrupting）**：用户要求暂停/取消/中止当前动作  
   - 期望行为：尽快停止当前 in-flight 调用（模型/工具），进入等待用户指令的状态。

如果把这两类输入都硬塞进“线性编排 + hooks”，就会出现职责混乱：
- hooks 天然是旁路（best-effort、非阻塞），不适合作为“等待用户输入”的关键路径。
- 编排如果自己 `poll_interrupt()`、自己维护 request_id、自己管理并发取消，会很快变得别扭且难以复验。

结论：引入运行期交互后，框架应从“线性 run”升级为“**会话状态机 + 副作用解释器**”。

---

## 2. 目标与非目标

### 2.1 目标

- **统一 streaming API**：CLI/Web/SDK 等不同交互层复用同一协议与语义。
- **同一条流承载全过程信息**：用户输入、LLM 输出、工具调用过程、修改内容（evidence/artifacts）、安全决策、暂停/恢复等。
- **编排确定性**：编排（Orchestrator）不直接做 I/O、不处理并发，纯函数式 step，易于测试与 replay。
- **运行期可中断**：支持 pause/cancel 等控制信号，尽快打断 in-flight 调用（best-effort）。
- **输入一致化**：审批/选择/确认/文本输入统一建模为“输入请求”。

### 2.2 非目标（本文不强制）

- 不要求一次性定义所有 UI 形态（A2UI 等可后续扩展）。
- 不强制 token-level streaming（可以先只发完整 model response）。

---

## 3. 核心架构：Orchestrator + Driver + Transport

### 3.1 角色定义

- **Orchestrator（编排器）**：纯状态机  
  - 只实现：`step(state, event) -> (new_state, effects[])`
  - 不做 I/O、不阻塞、不关心 streaming。

- **Driver（执行器）**：副作用解释器  
  - 执行 effects（模型调用/工具调用/请求输入/事件扇出）。
  - 负责并发：监听 transport 输入、管理 inbox、处理 interrupt、取消 in-flight effect。

- **Transport（传输层）**：具体 streaming 实现  
  - Stdio / WebSocket / SSE / 自定义 SDK 都是不同 transport。

### 3.2 总体数据流

```mermaid
flowchart TD
  subgraph O[Orchestrator = 纯状态机]
    STEP[step(state,event)\n-> state + effects[]]
  end
  subgraph D[Driver = 副作用解释器]
    LOOP[run loop\n- 串行处理 event\n- 执行 effects\n- 监听 transport\n- 可取消 in-flight]
    INBOX[Inbox Queue\n普通消息缓存]
    SIG[Interrupt Signal\npause/cancel]
  end
  subgraph T[Transport = Streaming]
    TX[send(msg)]
    RX[recv()->msg]
  end
  LOG[(IEventLog + Hooks)]

  RX --> LOOP
  LOOP --> INBOX
  LOOP --> SIG
  LOOP --> STEP
  STEP --> LOOP
  LOOP --> TX
  LOOP --> LOG
```

---

## 4. 关键机制：Inbox 与 Interrupt 分离

### 4.1 为什么必须分离

- 普通消息：不会立刻改变“当前正在做的事”，只是提供后续可用信息。
- 中断：必须改变“当前正在做的事”，触发取消、状态迁移（RUNNING -> PAUSED/WAITING）。

把两者混为一个接口会导致：编排层不得不同时处理“缓存输入”和“取消并发”，从而变得别扭。

### 4.2 行为约定（建议）

- `RequestInput` effect 执行时：
  1) **优先消费 inbox**（如果 inbox 中已有匹配输入，直接返回，不发送 input.request）。
  2) inbox 为空才发送 input.request 并等待 input.response。
- interrupt 到来时：
  - **保证**：不再启动新的外部调用（新的 model/tool 不会再被调度）。
  - **尽力**：取消正在进行的 in-flight 调用；若底层不可取消，允许其完成但结果被丢弃或标记为 cancelled。

---

## 5. 接口草案（最小可用）

> 说明：这里给“稳定语义接口”的形状；具体字段可在后续 spec 中细化。

### 5.1 Orchestrator：纯 step

```python
from dataclasses import dataclass
from typing import Literal, TypedDict


@dataclass(frozen=True)
class OrchestratorState:
    phase: Literal["WAIT_INPUT", "THINKING", "TOOLING", "PAUSED", "DONE"]
    pending_request_id: str | None = None
    # 其余：session/milestone/context 的可序列化快照


class OrchestratorEvent(TypedDict):
    type: str
    payload: dict


class Effect(TypedDict):
    type: str
    payload: dict


class IOrchestrator:
    def step(self, state: OrchestratorState, event: OrchestratorEvent) -> tuple[OrchestratorState, list[Effect]]:
        ...
```

### 5.2 Driver：解释 effects + 管理 transport/inbox/interrupt

```python
class ITransport:
    async def send(self, msg: dict) -> None: ...
    async def recv(self) -> dict: ...


class IRuntimeDriver:
    async def run(self, orch: IOrchestrator, init_state: OrchestratorState) -> None: ...
```

---

## 6. Effects 与 Events（建议最小集合）

### 6.1 Effects（Driver 执行的副作用）

- `EmitEvent`：记录/广播一个过程事件（扇出到 event_log、hooks、stream）
- `RequestInput`：请求用户输入（text/approve/select/confirm）
- `CallModel`：调用 `IModelAdapter.generate(...)`
- `InvokeTool`：调用 `IToolGateway.invoke(...)`
- （可选）`Backoff/Sleep`

> 约束：每个 effect 执行完成后必须回灌一个 event（成功/失败/被中断）。

### 6.2 Events（回灌给 Orchestrator 的事实）

- `InputProvided`：输入已获得（来自 inbox 消费或 input.response）
- `ModelResponded`：模型返回（含 tool_calls）
- `ToolFinished`：工具调用完成（含 ToolResult/evidence）
- `Interrupted`：收到 pause/cancel
- `ErrorOccurred`：执行器层面的错误（transport 断开、超时等）

---

## 7. Driver 运行循环（推荐语义）

Driver 的“确定性”来自两条规则：
1) **串行喂 event 给 Orchestrator**（同一 run 中的事件处理顺序可复现）
2) **同一时刻最多一个 in-flight effect**（实现最简单，审计最清晰）

执行要点：
- transport 输入分三类处理：
  - `user.message` -> inbox.enqueue（非打断）
  - `input.response` -> fulfill pending request（解除 RequestInput 等待）
  - `control.interrupt` -> cancel in-flight effect + enqueue `Interrupted` event（打断）
- `RequestInput` effect：
  - 优先消费 inbox；否则发送 `input.request` 并等待 `input.response`
- `CallModel/InvokeTool` effect：
  - 以“in-flight task vs interrupt”竞速实现可打断（best-effort cancellation）

---

## 8. Stdio（JSONL）示例协议（不含渲染）

### 8.1 Runtime -> Client（stdout）

- 过程事件：
```json
{"type":"event","event_type":"tool.invoke","payload":{"capability_id":"write_file","run_id":"r1"}}
```

- 输入请求：
```json
{"type":"input.request","request_id":"req_123","kind":"approve","payload":{"summary":"write_file path=...","risk":"idempotent_write"}}
```

### 8.2 Client -> Runtime（stdin）

- 普通消息（不打断）：
```json
{"type":"user.message","text":"补充：路径用 ./out.txt"}
```

- 输入响应：
```json
{"type":"input.response","request_id":"req_123","value":true}
```

- 中断（打断）：
```json
{"type":"control.interrupt","kind":"cancel","reason":"user requested stop"}
```

---

## 9. 与现有 DARE 组件的关系（映射建议）

- `IEventLog`：仍然是事实来源（WORM + replay）。`EmitEvent` effect 可以统一 append。
- hooks：订阅 `EmitEvent`（旁路、非阻塞、可失败），用于 stdout/metrics/脱敏/trace 等。
- `IExecutionControl`：可以逐步迁移为 Driver/Interaction 的内部能力：
  - pause/resume/checkpoint 可以映射为 `Interrupted(pause)` + `RequestInput(confirm/approve)` + 事件记录；
  - 或保留接口，但其默认实现内部调用 Driver 的 interrupt/request 机制。

---

## 10. 后续讨论建议（可作为下一次对齐点）

1) interrupt 的承诺边界：取消 in-flight 的 best-effort 需要哪些工具/模型适配支持？
2) 是否需要断线重连与“从某 event_id 续订”？（Web 常见需求）
3) event/effect 的最小字段：run_id/turn_id/correlation_id/visibility 等是否纳入硬约束？

