# Transport Domain 设计规范

> 版本: Draft v2  
> 状态: 待评审

---

## 1. 概述

Transport Domain 负责 **Client（用户端）与 Agent（编排端）之间的双向异步通信**。

### 设计原则

- **双向异步**：非请求-响应模式，双方可随时发送消息
- **关注点分离**：Client 和 Agent 各自只关心自己的收发逻辑
- **可扩展**：新增 Client 类型只需实现 MessageHandler

---

## 2. 接口定义 (Kernel)

```python
# === 基础接口 ===
class IOutputTransport(Protocol):
    """发送消息（由 Bridge 注入实现）"""
    async def send(self, msg: Message) -> None: ...

class IInputTransport(Protocol):
    """接收消息"""
    async def on_message(self, msg: Message) -> None: ...

class ITransport(IInputTransport, IOutputTransport, Protocol):
    """完整的双向 Transport"""
    pass

# === 消息处理 ===
class IMessageHandler(Protocol):
    """消息处理器（用户/Agent 实现）"""
    async def handle(self, msg: Message) -> None: ...

# === Transport Context ===
class ITransportContext(Protocol):
    """Transport 上下文（双方共用）"""
    async def put(self, msg: Message) -> None: ...
    def poll(self, msg_type: str | None = None) -> Message | None: ...

# === 角色专用接口 ===
class IClientTransport(ITransport, Protocol):
    """Client 侧 Transport 接口"""
    @property
    def context(self) -> ITransportContext: ...

class IAgentTransport(ITransport, Protocol):
    """Agent 侧 Transport 接口"""
    @property
    def context(self) -> "IAgentTransportContext": ...
    async def recv(self, msg_type: str | None = None) -> Message: ...
    def run_interruptible(self, coro) -> asyncio.Task: ...

class IAgentTransportContext(ITransportContext, Protocol):
    """Agent 侧扩展上下文"""
    async def get(self, msg_type: str | None = None) -> Message: ...
    def register_task(self, task: asyncio.Task) -> None: ...
    def cancel_all_tasks(self) -> None: ...
```

---

## 3. 消息协议

```python
@dataclass
class Message:
    type: str       # 消息类型
    payload: Any    # 消息内容
    timestamp: float = field(default_factory=time.time)
```

### 消息类型

| 方向 | type | payload | 说明 |
|------|------|---------|------|
| Client→Agent | `task` | `{text}` | 任务请求 |
| Client→Agent | `message` | `{text}` | 运行时补充 |
| Client→Agent | `authorize.response` | `{approved}` | 授权响应 |
| Client→Agent | `interrupt` | `{}` | 中断信号 |
| Agent→Client | `thinking` | `{content}` | LLM 思考 |
| Agent→Client | `response` | `{content}` | LLM 响应 |
| Agent→Client | `tool.start` | `{id, params}` | 工具开始 |
| Agent→Client | `tool.result` | `{id, result}` | 工具结果 |
| Agent→Client | `authorize.request` | `{id, summary}` | 请求授权 |
| Agent→Client | `complete` | `{success}` | 任务完成 |

> **注：** Tool 事件可通过 `ToolHookTransport` 从 Hook 系统桥接发送。

---

## 4. 架构

### 4.1 角色

```
┌─────────────────────────────────────────────────────────────────┐
│                       Processor (Bridge)                         │
│   创建 IOutputTransport 实例并注入给两侧，负责消息转发              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 │                 ▼
┌─────────────────┐         │         ┌─────────────────┐
│ ClientTransport │         │         │ AgentTransport  │
├─────────────────┤         │         ├─────────────────┤
│ output ─────────────────────────────────→ on_message  │
│ on_message ←───────────────────────────────── output  │
│ handler         │                   │ context         │
└─────────────────┘                   │ handler         │
                                      │ recv()          │
                                      └─────────────────┘
```

### 4.2 职责划分

| 角色 | 职责 |
|------|------|
| **IClientTransport** | 持有 `output` 发送消息，调用 `handler` 处理消息，管理 `context` |
| **IAgentTransport** | 持有 `output` 发送消息，提供 `recv()` 阻塞等待，管理扩展的 `context` |
| **Processor (Bridge)** | 创建 output 通道，连接两侧的 output → 对方的 on_message |
| **TransportContext** | 基础：消息缓冲 (`put`/`poll`) |
| **AgentTransportContext** | 扩展：阻塞等待 (`get`) + 可中断任务管理 |

---

## 5. 实现

### 5.1 ProcessorTransport

```python
class ProcessorTransport(ITransport):
    """抽象基类：包含消息处理 + 对端连接能力"""
    
    def __init__(self, handler: IMessageHandler):
        self._handler = handler
        self._peer: "ProcessorTransport | None" = None
    
    def connect(self, peer: "ProcessorTransport") -> None:
        """与对端 Transport 建立连接（双向）"""
        self._peer = peer
        if peer._peer is not self:
            peer.connect(self)
    
    async def send(self, msg: Message) -> None:
        """发送消息到对端"""
        if self._peer:
            await self._peer.on_message(msg)
    
    async def on_message(self, msg: Message) -> None:
        """接收消息并交给 handler 处理"""
        await self._handler.handle(msg)
```

### 5.2 ClientTransport

```python
class ClientTransport(ProcessorTransport, IClientTransport):
    """Client 侧：用户传入 MessageHandler"""
    
    def __init__(self, handler: IMessageHandler):
        super().__init__(handler)
        self._context = TransportContext()
    
    @property
    def context(self) -> TransportContext:
        return self._context
```

### 5.3 AgentTransport

```python
class AgentTransport(ProcessorTransport, IAgentTransport):
    """Agent 侧：内置 handler + 提供 recv()"""
    
    def __init__(self):
        self._context = AgentTransportContext()
        super().__init__(handler=AgentMessageHandler(self._context))
    
    @property
    def context(self) -> AgentTransportContext:
        return self._context
    
    async def recv(self, msg_type: str | None = None) -> Message:
        """阻塞等待消息"""
        return await self._context.get(msg_type)
    
    def run_interruptible(self, coro) -> asyncio.Task:
        """运行可被 interrupt 取消的协程"""
        task = asyncio.create_task(coro)
        self._context.register_task(task)
        return task


class AgentMessageHandler(IMessageHandler):
    """内置 handler：消息入队，interrupt 触发取消"""
    
    def __init__(self, context: AgentTransportContext):
        self._context = context
    
    async def handle(self, msg: Message) -> None:
        if msg.type == "interrupt":
            self._context.cancel_all_tasks()
        else:
            await self._context.put(msg)
```

### 5.4 TransportContext（基础）

```python
class TransportContext(ITransportContext):
    """基础上下文：消息缓冲（Client/Agent 共用）"""
    
    def __init__(self):
        self._queue: deque[Message] = deque()
    
    async def put(self, msg: Message) -> None:
        self._queue.append(msg)
    
    def poll(self, msg_type: str | None = None) -> Message | None:
        """非阻塞获取消息，无匹配返回 None"""
        for i, msg in enumerate(self._queue):
            if msg_type is None or msg.type == msg_type:
                del self._queue[i]
                return msg
        return None
```

### 5.5 AgentTransportContext（扩展）

```python
class AgentTransportContext(TransportContext, IAgentTransportContext):
    """Agent 侧扩展：阻塞等待 + 任务管理"""
    
    def __init__(self):
        super().__init__()
        self._event = asyncio.Event()
        self._tasks: dict[str, asyncio.Task] = {}
    
    async def put(self, msg: Message) -> None:
        await super().put(msg)
        self._event.set()  # 通知有新消息
    
    async def get(self, msg_type: str | None = None) -> Message:
        """阻塞等待匹配消息"""
        while True:
            msg = self.poll(msg_type)
            if msg:
                return msg
            self._event.clear()
            await self._event.wait()
    
    def register_task(self, task: asyncio.Task) -> None:
        key = str(id(task))
        self._tasks[key] = task
        task.add_done_callback(lambda _: self._tasks.pop(key, None))
    
    def cancel_all_tasks(self) -> None:
        for t in self._tasks.values():
            t.cancel()
        self._tasks.clear()
```



## 6. Client 扩展指南

### 用户需要做什么

1. **实现 `IMessageHandler`**：处理从 Agent 收到的消息
2. **通过 `transport.send()` 发送消息**：向 Agent 发送任务/授权/中断等

### 示例：CLI Client

```python
class CLIHandler(IMessageHandler):
    def __init__(self, transport: ClientTransport):
        self._transport = transport
    
    async def handle(self, msg: Message) -> None:
        match msg.type:
            case "response":
                print(msg.payload["content"])
            case "authorize.request":
                approved = input("Approve? (y/n): ") == "y"
                await self._transport.send(Message(
                    type="authorize.response",
                    payload={"approved": approved}
                ))
            case "complete":
                print("Done!")

# 初始化
client = ClientTransport(handler=CLIHandler(...))
agent = AgentTransport()
bridge = InProcessBridge(client, agent)

# 发送任务
await client.send(Message(type="task", payload={"text": "..."}))
```

---

## 7. Agent 集成

### 编排中使用

```python
class FiveLayerAgent:
    def __init__(self, transport: AgentTransport):
        self._transport = transport
    
    async def run(self, task: Task):
        # 发送思考中
        await self._transport.send(Message(type="thinking", ...))
        
        # 可中断的模型调用
        task = self._transport.run_interruptible(
            self._model.generate(prompt)
        )
        response = await task
        
        # 需要授权时
        await self._transport.send(Message(type="authorize.request", ...))
        auth = await self._transport.recv(msg_type="authorize.response")
        if not auth.payload["approved"]:
            return
```

---

## 8. Hook 桥接（可选）

```python
class ToolHookTransport:
    """将 Hook 事件桥接到 Transport"""
    
    def __init__(self, transport: AgentTransport):
        self._transport = transport
    
    async def on_tool_start(self, tool_id: str, params: dict):
        await self._transport.send(Message(type="tool.start", payload={...}))
    
    async def on_tool_result(self, tool_id: str, result: Any):
        await self._transport.send(Message(type="tool.result", payload={...}))
```

---

## 9. 未来扩展

| 场景 | 替换组件 |
|------|----------|
| 跨进程通信 | `InProcessBridge` → `WebSocketBridge` |
| 多 Client | 扩展 Bridge 支持广播 |
| 消息持久化 | 在 Bridge 中添加日志 |
