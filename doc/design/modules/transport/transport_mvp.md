# Transport Domain 设计文档（MVP）

> 状态：Draft / 待评审  
> 目标：为 Agent 与 Client（CLI / WebSocket / HTTP / Direct Test）提供一个轻量、可落地的消息交互骨架。  
> 核心原则：**Message 内容无关**、**编排解耦**、**默认阻塞回压**、**避免栈穿透**、**事件驱动 Bridge 不强制 start**。

---

## 目录

1. [目标与非目标](#1-目标与非目标)  
2. [核心概念与职责](#2-核心概念与职责)  
3. [Message 约定](#3-message-约定内容无关-envelope)  
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

1. **编排解耦**：Agent 侧仅依赖一个稳定接口 `AgentTransport`（`poll/send/run_interruptable/interrupt/start`）。
2. **统一接入**：不同 client 形态通过 `TransportBridge` 接入；Bridge 仅需要提供：
   - 注入 sender（client→agent）
   - 提供 receiver（agent→client）
3. **MVP 快速落地**：默认阻塞式回压（队列满则 await）。
4. **安全并发**：避免“send 直接触发 receiver”的栈穿透；消息投递通过队列 + pump task。

### 1.2 Non-goals

- 不自研网络协议/编解码/bytes framing（跨进程序列化留给 Bridge 自己实现）。
- 不实现 Netty 全套事件/flush/handler pipeline。
- 不在 Transport 内部管理 WebSocket/HTTP server 生命周期（server 属于接入层；每个会话实例化一个 Bridge）。

---

## 2. 核心概念与职责

本设计只有三个核心角色：`TransportBridge`、`Transport`、`AgentTransport`。

### 2.1 TransportBridge（Client 接入桥）

由 client 侧提供，用于桥接“外部会话世界”和“Agent 消息世界”。

**必需接口：**

1. `attach_agent_message_sender(sender)`  
   - `Transport.build()` 时注入  
   - Bridge 保存该 sender，在外部事件到来时调用它，将 client 输入发给 agent
2. `agent_message_receiver() -> receiver`  
   - Bridge 返回一个 receiver  
   - 当 agent 有输出消息时，Transport 内部投递泵会调用 receiver，将消息交付给 client（stdout / ws.send / future resolve 等）

**可选接口（仅需要自跑循环的 Bridge 才实现）：**

- `start()`：例如 Stdio 需要持续读 stdin（WebSocket/HTTP 通常不需要）
- `stop()`：MVP 可不实现，后续扩展

> WebSocket/HTTP 等事件驱动接入通常不需要 `start()`：输入由框架回调触发，Bridge 只在回调中调用保存的 sender。

---

### 2.2 Transport（构建与 wiring）

框架提供的构建入口：

- `Transport.build(bridge)`  
  - 创建一个固定实现的 `AgentTransport`  
  - 从 Bridge 获取 receiver  
  - 向 Bridge 注入 sender（用于将输入写入 `AgentTransport.inbox`）  
  - 返回 `AgentTransport` 给 AgentBuilder/Agent 使用

**对外只返回一个对象：`AgentTransport`**。  
Transport 内部不暴露 endpoint pair；“输出是另一个的输入”的连接关系通过函数引用注册 + 队列投递完成。

---

### 2.3 AgentTransport（Agent 稳定交互口，固定实现）

Agent 持有它，并通过它进行通信与中断控制。

**职责：**

- 维护两个队列：
  - `inbox`：client → agent（供 `poll()`）
  - `outbox`：agent → client（供 `send()`）
- 默认阻塞回压：
  - `poll()` 阻塞等输入
  - `send()` 若 outbox 满则 await
  - bridge sender 若 inbox 满则 await
- 在 `start()` 中启动内部 pump：
  - outbox → receiver：把 agent 输出投递给 client
- 提供中断语义：
  - `run_interruptable` 保存当前任务
  - `interrupt()` 取消当前任务（Task.cancel）

---

## 3. Message 约定（内容无关 Envelope）

Message payload 可以是：

- chunk（流式输出）
- thinking（思考过程）
- tool result（工具执行结果）
- slash command / prompt
- json 审批结果等

建议保留最小 envelope 以支持 ask/interrupt/streaming：

- `id: str`
- `reply_to: Optional[str]`
- `kind: "data" | "control"`
- `type: str`
- `payload: Any`
- `meta: dict`
- `stream_id: Optional[str]`
- `seq: Optional[int]`

**Interrupt 约定：**

- `kind="control"` 且 `type="interrupt"`

> MVP 阶段 interrupt 消息进入 inbox，由 agent 业务侧识别并调用 `transport.interrupt()`；  
> 或后续增强为：sender 收到 interrupt 立即抢占取消（非 MVP 必需）。

---

## 4. 接口定义（MVP）

### 4.1 Protocol 形式（Python typing）

```python
from typing import Protocol, Callable, Awaitable, Optional, Any, Dict

class Message(Protocol):
    id: str
    reply_to: Optional[str]
    kind: str
    type: str
    payload: Any
    meta: Dict[str, Any]
    stream_id: Optional[str]
    seq: Optional[int]

Sender   = Callable[[Message], Awaitable[None]]
Receiver = Callable[[Message], Awaitable[None]]

class TransportBridge(Protocol):
    def attach_agent_message_sender(self, sender: Sender) -> None: ...
    def agent_message_receiver(self) -> Receiver: ...

class AgentTransport(Protocol):
    async def start(self) -> None: ...
    async def poll(self) -> Message: ...
    async def send(self, msg: Message) -> None: ...
    async def run_interruptable(self, coro: Awaitable[Any]) -> Any: ...
    def interrupt(self) -> None: ...

class Transport(Protocol):
    @staticmethod
    def build(bridge: TransportBridge, *, max_inbox=100, max_outbox=100) -> AgentTransport: ...
```

---

## 5. 并发模型与泵（Pump）

### 5.1 关键约束：避免栈穿透

必须避免以下情况：

- Bridge 调用 sender 的调用栈中，直接执行 agent 的业务逻辑（会导致递归/重入/难以回压）
- Agent 调用 `send()` 的调用栈中，直接执行 bridge receiver（会导致栈穿透、吞吐不稳定、异常边界不清晰）

因此约定：

- sender **只入队** `inbox`（可能阻塞回压）
- `send()` **只入队** `outbox`（可能阻塞回压）
- receiver 的调用通过 pump task 异步完成

### 5.2 AgentTransport.start() 启动 outbox → receiver 的投递泵

`AgentTransport.start()` 启动一个后台任务（pump）：

- `msg = await outbox.get()`
- `await receiver(msg)`

这样即使 WebSocket Bridge 没有 `start()`，仍能持续收到 agent 输出。

### 5.3 Agent 的运行模型建议

Agent 侧通常做两件事：

1. `await transport.start()`（启动投递泵）
2. 业务循环：`msg = await transport.poll()` → `process(msg)` → `await transport.send(output)`

---

## 6. 数据流与控制流

### 6.1 client → agent（输入）

1. 外部事件源（stdin/ws/http callback）构造 Message
2. Bridge 在事件回调中调用保存的 `sender(msg)`
3. sender 将 msg `await inbox.put(msg)`（阻塞回压）
4. agent 业务循环 `await transport.poll()` 得到 msg 并处理

### 6.2 agent → client（输出）

1. agent 调用 `await transport.send(msg)` → `await outbox.put(msg)`
2. outbox pump 从 outbox 取 msg 并调用 `await receiver(msg)`
3. receiver 将消息写到 stdout/ws/http response/resolve future

### 6.3 interrupt（MVP）

1. Bridge 发送 interrupt 消息：`Message(kind="control", type="interrupt")`（进入 inbox）
2. agent 侧在处理该消息时调用 `transport.interrupt()`
3. interrupt 取消当前 `run_interruptable` 任务

---

## 7. 回压策略（MVP：默认阻塞）

- `inbox` / `outbox` 都有 `maxsize`
- 队列满则 `await put()` 阻塞
- MVP 不做 drop/merge/priority；后续如需 streaming 优化，可在 outbox pump 中做合并策略（不影响接口）

---

## 8. 使用方式

### 8.1 WebSocket（事件驱动，无需 bridge.start）

```python
bridge = WebSocketBridge(ws)       # 实现 sender 注入 + receiver 返回
transport = Transport.build(bridge)

agent = AgentBuilder().with_transport(transport).build()
await agent.start()                # agent.start 内部会调用 transport.start()

# ws 框架回调：
# await bridge.handle_ws_message(raw)  # 内部调用保存的 sender(msg)
```

### 8.2 Stdio（需要输入循环，所以 bridge.start）

```python
bridge = StdioBridge()
transport = Transport.build(bridge)

agent = AgentBuilder().with_transport(transport).build()
await asyncio.gather(agent.start(), bridge.start())
```

### 8.3 DirectClient（ask）

```python
bridge = DirectClientBridge()
transport = Transport.build(bridge)

agent = AgentBuilder().with_transport(transport).build()
await agent.start()

resp = await bridge.ask(req)
```

---

## 9. 参考实现骨架（Python asyncio）

> 说明：这是 MVP 参考实现，用于指导开发拆分；错误处理/关闭语义可后续迭代。

```python
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol

# ---------- Message ----------

@dataclass
class Message:
    id: str
    reply_to: Optional[str] = None
    kind: str = "data"       # "data" | "control"
    type: str = "message"    # "prompt"|"chunk"|...|"interrupt"
    payload: Any = None
    meta: Dict[str, Any] = field(default_factory=dict)
    stream_id: Optional[str] = None
    seq: Optional[int] = None

def new_id() -> str:
    return uuid.uuid4().hex

Sender   = Callable[[Message], Awaitable[None]]
Receiver = Callable[[Message], Awaitable[None]]

# ---------- Bridge ----------

class TransportBridge(Protocol):
    def attach_agent_message_sender(self, sender: Sender) -> None: ...
    def agent_message_receiver(self) -> Receiver: ...

# ---------- AgentTransport ----------

class AgentTransport(Protocol):
    async def start(self) -> None: ...
    async def poll(self) -> Message: ...
    async def send(self, msg: Message) -> None: ...
    async def run_interruptable(self, coro: Awaitable[Any]) -> Any: ...
    def interrupt(self) -> None: ...

# ---------- Transport (builder) ----------

class Transport:
    @staticmethod
    def build(bridge: TransportBridge, *, max_inbox=100, max_outbox=100) -> AgentTransport:
        return DefaultAgentTransport(bridge, max_inbox=max_inbox, max_outbox=max_outbox)

# ---------- DefaultAgentTransport (固定实现) ----------

class DefaultAgentTransport(AgentTransport):
    def __init__(self, bridge: TransportBridge, *, max_inbox: int, max_outbox: int):
        self._bridge = bridge
        self._receiver: Receiver = bridge.agent_message_receiver()

        self._inbox: asyncio.Queue[Message] = asyncio.Queue(maxsize=max_inbox)
        self._outbox: asyncio.Queue[Message] = asyncio.Queue(maxsize=max_outbox)

        self._current_task: Optional[asyncio.Task] = None
        self._started = False
        self._out_pump_task: Optional[asyncio.Task] = None

        # 注入 sender：client -> agent（只入队，默认阻塞回压）
        async def sender(msg: Message) -> None:
            await self._inbox.put(msg)

        bridge.attach_agent_message_sender(sender)

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._out_pump_task = asyncio.create_task(self._pump_outbox_to_receiver())

    async def poll(self) -> Message:
        return await self._inbox.get()

    async def send(self, msg: Message) -> None:
        await self._outbox.put(msg)

    def interrupt(self) -> None:
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()

    async def run_interruptable(self, coro: Awaitable[Any]) -> Any:
        self._current_task = asyncio.create_task(coro)
        try:
            return await self._current_task
        finally:
            self._current_task = None

    async def _pump_outbox_to_receiver(self) -> None:
        while True:
            msg = await self._outbox.get()
            await self._receiver(msg)

# ---------- Example: StdioBridge ----------

class StdioBridge:
    def __init__(self):
        self._sender: Optional[Sender] = None

    def attach_agent_message_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_message_receiver(self) -> Receiver:
        async def recv(msg: Message) -> None:
            print(f"[agent] {msg.type}: {msg.payload}")
        return recv

    async def start(self) -> None:
        assert self._sender is not None
        while True:
            line = await asyncio.to_thread(input, "> ")
            line = line.strip()
            if not line:
                continue
            await self._sender(Message(id=new_id(), type="prompt", payload=line))

# ---------- Example: WebSocketBridge (事件驱动，无需 start) ----------

class WebSocketBridge:
    def __init__(self, ws):
        self.ws = ws
        self._sender: Optional[Sender] = None

    def attach_agent_message_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_message_receiver(self) -> Receiver:
        async def recv(msg: Message) -> None:
            await self.ws.send(str({"type": msg.type, "payload": msg.payload, "reply_to": msg.reply_to}))
        return recv

    async def handle_ws_message(self, raw: str) -> None:
        assert self._sender is not None
        await self._sender(Message(id=new_id(), type="prompt", payload=raw))

# ---------- Example: DirectClientBridge (ask) ----------

class DirectClientBridge:
    def __init__(self):
        self._sender: Optional[Sender] = None
        self._pending: Dict[str, asyncio.Future] = {}

    def attach_agent_message_sender(self, sender: Sender) -> None:
        self._sender = sender

    def agent_message_receiver(self) -> Receiver:
        async def recv(msg: Message) -> None:
            if msg.reply_to and msg.reply_to in self._pending:
                fut = self._pending[msg.reply_to]
                if not fut.done():
                    fut.set_result(msg)
        return recv

    async def ask(self, req: Message, timeout: float = 30.0) -> Message:
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
2. stop/close 语义：transport/agent/bridge 如何优雅退出、取消 pump task、清理 pending
3. outbox 合并/限频：对 chunk/thinking 做合并策略
4. 错误处理：receiver 抛异常如何处理（是否停泵、是否上报）