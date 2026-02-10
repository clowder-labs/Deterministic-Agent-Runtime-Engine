# Transport Domain 设计文档（MVP）

> 状态：Draft / 待评审
> 目标：为 Agent 与 Client（CLI / WebSocket / HTTP / Direct Test）提供一个轻量、可落地的消息交互骨架。
> 核心原则：**TransportEnvelope 内容无关**、**编排解耦**、**默认阻塞回压**、**避免栈穿透**、**事件驱动 Protocol 不强制 start**。

---

## 目录

1. [目标与非目标](#1-目标与非目标)
2. [核心概念与职责](#2-核心概念与职责)
3. [TransportEnvelope 约定](#3-transportenvelope-约定内容无关-envelope)
4. [接口定义（MVP）](#4-接口定义mvp)
5. [并发模型与泵（Pump）](#5-并发模型与泵pump)
6. [数据流与控制流](#6-数据流与控制流)
7. [回压策略（MVP：默认阻塞）](#7-回压策略mvp默认阻塞)
8. [使用方式](#8-使用方式)
9. [参考实现骨架（Python asyncio）](#9-参考实现骨架python-asyncio)
10. [后续扩展（非 MVP）](#10-后续扩展非-mvp)

---

## 1. 目标与非目标

### 1.1 Goals

1. **编排解耦**：Agent 侧仅依赖一个稳定接口 `AgentChannel`（`poll/send/start/stop`）。
2. **统一接入**：不同 client 形态通过 `ClientChannel` 接入；ClientChannel 仅需要提供：
   - 注入 sender（client→agent）
   - 提供 receiver（agent→client）
3. **MVP 快速落地**：默认阻塞式回压（队列满则 await）。
4. **安全并发**：避免“send 直接触发 receiver”的栈穿透；消息投递通过队列 + pump task。

### 1.2 Non-goals

- 不自研网络协议/编解码/bytes framing（跨进程序列化留给 ClientChannel 自己实现）。
- 不实现 Netty 全套事件/flush/handler pipeline。
- 不在 AgentChannel 内部管理 WebSocket/HTTP server 生命周期（server 属于接入层；每个会话实例化一个 ClientChannel）。

---

## 2. 核心概念与职责

本设计只有三个核心角色：`ClientChannel`、`AgentChannel`、`TransportEnvelope`。

### 2.1 ClientChannel（Client 接入桥）

由 client 侧提供，用于桥接“外部会话世界”和“Agent 消息世界”。

**必需接口：**

1. `attach_agent_envelope_sender(sender)`
   - `AgentChannel.build()` 时注入
   - ClientChannel 保存该 sender，在外部事件到来时调用它，将 client 输入发给 agent
2. `agent_envelope_receiver() -> receiver`
   - ClientChannel 返回一个 receiver
   - 当 agent 有输出消息时，AgentChannel 内部投递泵会调用 receiver，将消息交付给 client（stdout / ws.send / future resolve 等）

**可选接口（仅需要自跑循环的 ClientChannel 才实现）：**

- `start()`：例如 Stdio 需要持续读 stdin（WebSocket/HTTP 通常不需要）
- `stop()`：可选；用于关闭输入循环（若有）

> WebSocket/HTTP 等事件驱动接入通常不需要 `start()`：输入由框架回调触发，ClientChannel 只在回调中调用保存的 sender。

---

### 2.2 AgentChannel.build（构建与 wiring）

框架提供的构建入口：

- `AgentChannel.build(client_channel)`
  - 创建一个固定实现的 `AgentChannel`
  - 从 ClientChannel 获取 receiver
  - 向 ClientChannel 注入 sender（用于将输入写入 `AgentChannel.inbox`）
  - 返回 `AgentChannel` 给 AgentBuilder/Agent 使用

> MVP 默认实现为 `DefaultAgentChannel(...)`，对外以 `AgentChannel.build` 作为唯一构建入口。

**对外只返回一个对象：`AgentChannel`**。
AgentChannel 内部不暴露 endpoint pair；“输出是另一个的输入”的连接关系通过函数引用注册 + 队列投递完成。

---

### 2.3 AgentChannel（Agent 稳定交互口，固定实现）

Agent 持有它，并通过它进行通信。

**职责：**

- 维护两个队列：
  - `inbox`：client → agent（供 `poll()`）
  - `outbox`：agent → client（供 `send()`）
- 默认阻塞回压：
  - `poll()` 阻塞等输入
  - `send()` 若 outbox 满则 await
  - ClientChannel sender 若 inbox 满则 await
- 在 `start()` 中启动内部 pump：
  - outbox → receiver：把 agent 输出投递给 client
- `start()` 幂等；重复调用不应启动多个 pump
- `stop()` 停止投递泵，允许丢弃待发送消息（不保证 flush）
- receiver/sender 异常记录日志但不中断泵与通道
- 可选 encoder/decoder 在 AgentChannel 边界做 envelope 变换（例如 schema 适配或脱敏）
- 若 ClientChannel 需要输入循环（如 stdio），需要由调用方显式启动 `client_channel.start()`
- 中断由上层交互分发器（agent/dispatcher）维护 in-flight 任务并取消；`AgentChannel` 仅转发 `kind="control"` 消息

---

## 3. TransportEnvelope 约定（内容无关 Envelope）

TransportEnvelope payload 可以是：

- chunk（流式输出）
- thinking（思考过程）
- tool result（工具执行结果）
- slash command / prompt
- json 审批结果等

建议保留最小 envelope 以支持 ask/interrupt/streaming：

- `id: str`
- `reply_to: Optional[str]`
- `kind: "message" | "action" | "control"`
- `payload: Any`
- `meta: dict`
- `stream_id: Optional[str]`
- `seq: Optional[int]`

> `TransportEnvelope` 与 `context.Message` 解耦，transport 层不假设对话语义。
> 若提供 `stream_id/seq`，要求同一 stream 内 `seq` 单调递增；接收顺序以队列顺序为准，不做重排。

**动作/控制约定：**

- `kind="action"` 且 `payload="<resource:action>"`（例如 `tools:list`）
- `kind="control"` 且 `payload="<agent-control>"`（例如 `interrupt`）

> `TransportEnvelope` 不再需要额外的 `type` 字段；路由由 `kind + payload` 决定。

---

## 4. 接口定义（MVP）

### 4.1 ClientChannel 形式（Python typing）

```python
from typing import Protocol, Callable, Awaitable, Optional, Any, Dict

class TransportEnvelope(Protocol):
    id: str
    reply_to: Optional[str]
    kind: str
    payload: Any
    meta: Dict[str, Any]
    stream_id: Optional[str]
    seq: Optional[int]

Sender   = Callable[[TransportEnvelope], Awaitable[None]]
Receiver = Callable[[TransportEnvelope], Awaitable[None]]
Encoder  = Callable[[TransportEnvelope], TransportEnvelope]
Decoder  = Callable[[TransportEnvelope], TransportEnvelope]

class ClientChannel(Protocol):
    def attach_agent_envelope_sender(self, sender: Sender) -> None: ...
    def agent_envelope_receiver(self) -> Receiver: ...

class AgentChannel(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def poll(self) -> TransportEnvelope: ...
    async def send(self, msg: TransportEnvelope) -> None: ...
    @staticmethod
    def build(
        client_channel: ClientChannel,
        *,
        max_inbox=100,
        max_outbox=100,
        encoder: Callable[[TransportEnvelope], TransportEnvelope] | None = None,
        decoder: Callable[[TransportEnvelope], TransportEnvelope] | None = None,
    ) -> "AgentChannel": ...
```

---

## 5. 并发模型与泵（Pump）

### 5.1 关键约束：避免栈穿透

必须避免以下情况：

- ClientChannel 调用 sender 的调用栈中，直接执行 agent 的业务逻辑（会导致递归/重入/难以回压）
- Agent 调用 `send()` 的调用栈中，直接执行 ClientChannel receiver（会导致栈穿透、吞吐不稳定、异常边界不清晰）

因此约定：

- sender **只入队** `inbox`（可能阻塞回压）
- `send()` **只入队** `outbox`（可能阻塞回压）
- receiver 的调用通过 pump task 异步完成

### 5.2 AgentChannel.start() 启动 outbox → receiver 的投递泵

`AgentChannel.start()` 启动一个后台任务（pump）：

- `msg = await outbox.get()`
- `await receiver(msg)`
- receiver 抛异常需记录日志并继续泵送后续消息

这样即使 WebSocket ClientChannel 没有 `start()`，仍能持续收到 agent 输出。

### 5.3 Agent 的运行模型建议

Agent 侧通常做两件事：

1. `await channel.start()`（启动投递泵）
2. 业务循环：`msg = await channel.poll()` → `process(msg)` → `await channel.send(output)`

> Agent 持有 `AgentChannel` 并在编排内部直接调用其方法（无需额外的 loop helper）。

---

## 6. 数据流与控制流

### 6.1 client → agent（输入）

1. 外部事件源（stdin/ws/http callback）构造 TransportEnvelope
2. ClientChannel 在事件回调中调用保存的 `sender(msg)`
3. sender 将 msg `await inbox.put(msg)`（阻塞回压）
4. agent 业务循环 `await channel.poll()` 得到 msg 并处理

### 6.2 agent → client（输出）

1. agent 调用 `await channel.send(msg)` → `await outbox.put(msg)`
2. outbox pump 从 outbox 取 msg 并调用 `await receiver(msg)`
3. receiver 将消息写到 stdout/ws/http response/resolve future

### 6.3 interrupt（MVP）

1. ClientChannel 发送 interrupt 消息：`TransportEnvelope(kind="control", payload="interrupt")`（进入 inbox）
2. agent/dispatcher 侧在处理该消息时调用 `agent.interrupt()`
3. `agent.interrupt()` 取消当前 in-flight 任务

---

## 7. 回压策略（MVP：默认阻塞）

- `inbox` / `outbox` 都有 `maxsize`
- 队列满则 `await put()` 阻塞
- MVP 不做 drop/merge/priority；后续如需 streaming 优化，可在 outbox pump 中做合并策略（不影响接口）

---

## 8. 使用方式

### 8.1 WebSocket（事件驱动，无需 ClientChannel.start）

```python
client_channel = WebSocketClientChannel(ws)  # 实现 sender 注入 + receiver 返回
channel = AgentChannel.build(client_channel)

agent = AgentBuilder().with_agent_channel(channel).build()
await agent.start()

# ws 框架回调：
# await client_channel.handle_ws_message(raw)  # 内部调用保存的 sender(msg)
# agent.start() 会启动内部 poll loop，无需额外执行
```

### 8.2 Stdio（需要输入循环，需要 ClientChannel.start）

```python
client_channel = StdioClientChannel()
channel = AgentChannel.build(client_channel)

agent = AgentBuilder().with_agent_channel(channel).build()
await agent.start()
await client_channel.start()
```

### 8.3 DirectClientChannel（ask）

```python
client_channel = DirectClientChannel()
channel = AgentChannel.build(client_channel)

agent = AgentBuilder().with_agent_channel(channel).build()
await agent.start()

resp = await client_channel.ask(req)
```

### 8.4 WebSocket / A2A 推荐 envelope 形状

- Prompt（默认消息）：
  - `{"kind": "message", "payload": "请总结当前项目结构"}`
- Deterministic action：
  - `{"kind": "action", "payload": "tools:list"}`
- Runtime control：
  - `{"kind": "control", "payload": "interrupt"}`

> A2A/JSON-RPC 接入时，建议在协议适配层把上层请求映射到同样的 `kind/payload` 形状，再转发给 transport channel；避免通过 prompt 文本解析 action/control。

---

## 9. 参考实现骨架（Python asyncio）

> 说明：这是 MVP 参考实现，用于指导开发拆分；错误处理/关闭语义可后续迭代。

```python
import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol

# ---------- TransportEnvelope ----------

@dataclass
class TransportEnvelope:
    id: str
    reply_to: Optional[str] = None
    kind: str = "message"    # "message" | "action" | "control"
    payload: Any = None
    meta: Dict[str, Any] = field(default_factory=dict)
    stream_id: Optional[str] = None
    seq: Optional[int] = None

def new_id() -> str:
    return uuid.uuid4().hex

Sender   = Callable[[TransportEnvelope], Awaitable[None]]
Receiver = Callable[[TransportEnvelope], Awaitable[None]]

# ---------- ClientChannel ----------

class ClientChannel(Protocol):
    def attach_agent_envelope_sender(self, sender: Sender) -> None: ...
    def agent_envelope_receiver(self) -> Receiver: ...

# ---------- AgentChannel ----------

class AgentChannel(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def poll(self) -> TransportEnvelope: ...
    async def send(self, msg: TransportEnvelope) -> None: ...
    @staticmethod
    def build(
        client_channel: ClientChannel,
        *,
        max_inbox=100,
        max_outbox=100,
        encoder: Encoder | None = None,
        decoder: Decoder | None = None,
    ) -> "AgentChannel": ...

# ---------- DefaultAgentChannel (固定实现；AgentChannel.build 默认实现) ----------

class DefaultAgentChannel(AgentChannel):
    @staticmethod
    def build(
        client_channel: ClientChannel,
        *,
        max_inbox=100,
        max_outbox=100,
        encoder: Encoder | None = None,
        decoder: Decoder | None = None,
    ) -> "AgentChannel":
        """Factory for the default channel (used by AgentChannel.build)."""
        return DefaultAgentChannel(
            client_channel,
            max_inbox=max_inbox,
            max_outbox=max_outbox,
            encoder=encoder,
            decoder=decoder,
        )

    def __init__(
        self,
        client_channel: ClientChannel,
        *,
        max_inbox: int,
        max_outbox: int,
        encoder: Encoder | None,
        decoder: Decoder | None,
    ):
        self._client = client_channel
        self._receiver: Receiver = client_channel.agent_envelope_receiver()
        self._encoder = encoder or (lambda env: env)
        self._decoder = decoder or (lambda env: env)

        self._inbox: asyncio.Queue[TransportEnvelope] = asyncio.Queue(maxsize=max_inbox)
        self._outbox: asyncio.Queue[TransportEnvelope] = asyncio.Queue(maxsize=max_outbox)

        self._started = False
        self._out_pump_task: Optional[asyncio.Task] = None

        # 注入 sender：client -> agent（只入队，默认阻塞回压）
        async def sender(msg: TransportEnvelope) -> None:
            try:
                await self._inbox.put(self._decoder(msg))
            except Exception:
                logging.exception("agent channel sender failed")

        client_channel.attach_agent_envelope_sender(sender)

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._out_pump_task = asyncio.create_task(self._pump_outbox_to_receiver())

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        if self._out_pump_task:
            self._out_pump_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._out_pump_task
        # Drop pending outgoing messages by draining the queue.
        while not self._outbox.empty():
            self._outbox.get_nowait()

    async def poll(self) -> TransportEnvelope:
        return await self._inbox.get()

    async def send(self, msg: TransportEnvelope) -> None:
        try:
            encoded = self._encoder(msg)
        except Exception:
            logging.exception("agent channel encoder failed")
            return
        await self._outbox.put(encoded)

    async def _pump_outbox_to_receiver(self) -> None:
        while True:
            msg = await self._outbox.get()
            try:
                await self._receiver(msg)
            except Exception:
                logging.exception("agent channel receiver failed")

# ---------- Example: StdioClientChannel ----------

class StdioClientChannel:
    def __init__(self):
        self._sender: Optional[Sender] = None

    def attach_agent_envelope_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_envelope_receiver(self) -> Receiver:
        async def recv(msg: TransportEnvelope) -> None:
            print(f"[agent] {msg.payload}")
        return recv

    async def start(self) -> None:
        assert self._sender is not None
        while True:
            line = await asyncio.to_thread(input, "> ")
            line = line.strip()
            if not line:
                continue
            await self._sender(TransportEnvelope(id=new_id(), kind="message", payload=line))

# ---------- Example: WebSocketClientChannel (事件驱动，无需 start) ----------

class WebSocketClientChannel:
    def __init__(self, ws):
        self.ws = ws
        self._sender: Optional[Sender] = None

    def attach_agent_envelope_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_envelope_receiver(self) -> Receiver:
        async def recv(msg: TransportEnvelope) -> None:
            await self.ws.send(str({"kind": msg.kind, "payload": msg.payload, "reply_to": msg.reply_to}))
        return recv

    async def handle_ws_message(self, raw: str) -> None:
        assert self._sender is not None
        await self._sender(TransportEnvelope(id=new_id(), kind="message", payload=raw))

# ---------- Example: DirectClientChannel (ask) ----------

class DirectClientChannel:
    def __init__(self):
        self._sender: Optional[Sender] = None
        self._pending: Dict[str, asyncio.Future] = {}

    def attach_agent_envelope_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_envelope_receiver(self) -> Receiver:
        async def recv(msg: TransportEnvelope) -> None:
            if msg.reply_to and msg.reply_to in self._pending:
                fut = self._pending[msg.reply_to]
                if not fut.done():
                    fut.set_result(msg)
        return recv

    async def ask(self, req: TransportEnvelope, timeout: float = 30.0) -> TransportEnvelope:
        assert self._sender is not None
        if not req.id:
            req.id = new_id()
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending[req.id] = fut
        try:
            await self._sender(req)
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(req.id, None)
```

---

## 10. 后续扩展（非 MVP）

1. interrupt 抢占：sender 收到 interrupt 是否立即 cancel，而不是等 agent poll
2. drain/flush 语义：`stop()` 时是否等待 outbox 清空或提供超时策略
3. outbox 合并/限频：对 chunk/thinking 做合并策略
4. 错误策略：重试/退避/指标上报等更细粒度策略
