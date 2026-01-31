# Transport Domain 设计规范 (Synthesized)

> 版本: Draft v4  
> 状态: 待评审
> 核心：基础 I/O 接口 (ITransport) + 责任链模型 (Pipeline)

---

## 1. 核心愿景 (Design Philosophy)

本规范旨在整合**底层通信的简洁性**与**逻辑处理的高扩展性**。通过将对称的 I/O 接口作为物理底座，叠加 Netty 风格的责任链模型，实现：

- **物理对称性**：底层通信始终基于 `on_message` 和 `send`，保持两端一致。
- **协议无关性**：Agent 业务逻辑无需关心底层物理实现。
- **控制与数据平面分离**：高性能的抢占式指令（控制面）与有序的消息流（数据面）并行。
- **拉取式消费**：通过 `AgentContext` 将异步推送转换为阻塞式拉取，降低业务复杂度。

---

## 2. 基础通信接口 (The Plumbing)

这是框架最底层的通信原语，确保所有传输实现（同进程、TCP、WebSocket）具有统一的行为。

```python
class IInputTransport(Protocol):
    """入站接口：接收来自对端的消息"""
    async def on_message(self, msg: Message) -> None: ...

class IOutputTransport(Protocol):
    """出站接口：向对端发送消息"""
    async def send(self, msg: Message) -> None: ...

class ITransport(IInputTransport, IOutputTransport, Protocol):
    """双向通信接口"""
    pass
```

---

## 3. 逻辑架构组件 (The Engine)

在基础 I/O 接口之上，构建逻辑处理层。

### 3.1 Channel (通道)
`Channel` 是 `ITransport` 的具体实现，它：
- 持有物理连接（或本身就是物理连接）。
- 持有一个 `Pipeline` 负责逻辑处理。
- 当 `on_message` 被调用时，将消息推入 Pipeline 的入站流程。

### 3.2 Pipeline & Handler (分层处理)
- **Pipeline**: 管理一个 `IMessageHandler` 链表。
- **IMessageHandler**: 处理入站/出站消息或 User Event（如中断信号）。

### 3.3 AgentContext (业务接口)
Agent 实例能看到的唯一高级接口，彻底隔离传输细节：
- **poll()**: 阻塞式拉取经过 Pipeline 处理后的业务消息。
- **send(msg)**: 发送消息，触发 Pipeline 的出站流程。
- **set_interrupt_handler(cb)**: 注册中断指令的回调。

---

## 4. 核心接口定义 (Kernel)

```python
# === 1. 逻辑层接口 (Netty Style) ===
class IAgentTransportContext(Protocol):
    """Agent 专用高级接口"""
    async def send(self, msg: Message) -> None: ...
    async def poll(self) -> Message: ... # 阻塞式拉取
    def set_interrupt_handler(self, callback: Callable): ...

class IMessageHandler(Protocol):
    """责任链处理器"""
    async def handle_inbound(self, ctx: "IHandlerContext", msg: Any): ...
    async def handle_outbound(self, ctx: "IHandlerContext", msg: Any): ...
    async def user_event_triggered(self, ctx: "IHandlerContext", event: Any): ...

# === 2. 桥接层接口 ===
class IChannel(ITransport, Protocol):
    """通道：既是物理端点，也是逻辑入口"""
    @property
    def pipeline(self) -> "IPipeline": ...

class IHandlerContext(Protocol):
    """Handler 执行上下文"""
    async def fire_channel_read(self, msg: Any): ...
    async def fire_user_event_triggered(self, event: Any): ...
    async def write(self, msg: Any): ... # 触发下级出站
```

---

## 5. 全链路交互流程 (Workflow)

### 5.1 数据流 (Data Plane - 任务流)
1. **上游输入**：物理层调用 `Channel.on_message(msg)`。
2. **流水线处理**：`Channel` 触发 `pipeline.fire_channel_read(msg)`。
3. **缓冲消费**：`AgentExecuteHandler` 将消息存入 `asyncio.Queue`，Agent 通过 `await context.poll()` 激活。

### 5.2 控制流 (Control Plane - 抢占流)
1. **识别信号**：`MessageDecoder` 在入站过程中识别出系统指令。
2. **广播事件**：通过 `ctx.fire_user_event_triggered(InterruptEvent())` 广播。
3. **即时抢占**：`AgentExecuteHandler` 捕获事件，立即执行 Agent 注册的回调，不进入数据队列。

---

## 6. 核心实现示例

### 6.1 ProcessorChannel (同进程对称连接)

```python
class ProcessorChannel(IChannel):
    """内存级双向管道容器"""
    def __init__(self):
        self._pipeline = DefaultPipeline()
        self._output = _ChannelOutput(self) # 内部类持有对本通道的引用
    
    @staticmethod
    def pair() -> tuple["ProcessorChannel", "ProcessorChannel"]:
        """创建一个相互连接的对等管道对"""
        a, b = ProcessorChannel(), ProcessorChannel()
        a.connect_peer(b)
        b.connect_peer(a)
        return a, b

    def connect_peer(self, peer: "ProcessorChannel"):
        # 建立物理连接逻辑（内部实现）
        self._output.set_peer(peer)

    # IInputTransport 实现：对端调用
    async def on_message(self, msg: Message):
        await self._pipeline.fire_channel_read(msg)

    # IOutputTransport 实现：供 Pipeline 尾部调用输出
    async def send(self, msg: Message):
        await self._output.send(msg)

class _ChannelOutput(IOutputTransport):
    """内部输出类：负责跨通道的消息接力"""
    def __init__(self, owner: ProcessorChannel):
        self._owner = owner
        self._peer: ProcessorChannel | None = None
        
    def set_peer(self, peer: ProcessorChannel):
        self._peer = peer
        
    async def send(self, msg: Message):
        if self._peer:
            # 物理上调用对端的入站接口
            await self._peer.on_message(msg)
```

### 6.2 Agent 集成：Context 与 Handler 分离

```python
class AgentTransportContext(IAgentTransportContext):
    """业务状态持有者：处理 Queue 的读写与中断映射"""
    def __init__(self, max_buffer=100):
        self._queue = asyncio.Queue(maxsize=max_buffer)
        self._interrupt_cb: Callable | None = None
        self._pipeline_ctx: IHandlerContext | None = None

    # 由 AgentExecuteHandler 调用
    async def push_message(self, msg: Message):
        await self._queue.put(msg)
        
    def trigger_interrupt(self):
        if self._interrupt_cb: self._interrupt_cb()

    def set_pipeline_ctx(self, ctx: IHandlerContext):
        self._pipeline_ctx = ctx

    # IAgentTransportContext (业务接口) 实现
    async def poll(self) -> Message:
        return await self._queue.get()

    async def send(self, msg: Message):
        if self._pipeline_ctx:
            await self._pipeline_ctx.write(msg)

    def set_interrupt_handler(self, callback: Callable):
        self._interrupt_cb = callback

class AgentExecuteHandler(IMessageHandler):
    """执行器处理器：仅负责将入站消息分发给关联的 Context"""
    def __init__(self, context: AgentTransportContext):
        self._context = context

    async def handle_inbound(self, ctx: IHandlerContext, msg: Message):
        # 建立 Context 与 Pipeline 的回传通道
        self._context.set_pipeline_ctx(ctx)
        # 存入业务层队列
        await self._context.push_message(msg)

    async def user_event_triggered(self, ctx: IHandlerContext, event: Any):
        if isinstance(event, InterruptEvent):
            # 触发业务层定义的回调
            self._context.trigger_interrupt()

class BaseAgent:
    """业务 Agent 基类"""
    def __init__(self, context: IAgentTransportContext):
        self.context = context # 业务逻辑通过 Context 消费

    async def run(self):
        while True:
            msg = await self.context.poll() # 从 Context 拉取
            await self.process(msg)
```

### 6.3 StdioClientTransport (终端桥接实现)
```python
class StdioClientTransport(IChannel):
    """Stdio 传输层：包装终端流并持有 Pipeline"""
    def __init__(self):
        self._pipeline = DefaultPipeline()
        # Stdio 本身就是物理端点，没有对端引用

    # IInputTransport 实现：外部输入触发
    async def on_message(self, msg: Message):
        # 此处 msg 可能是从 stdin 解析出来的
        await self._pipeline.fire_channel_read(msg)

    # IOutputTransport 实现：逻辑层发送到物理层
    async def send(self, msg: Message):
        # 序列化并输出到 stdout
        print(serialize(msg), flush=True)

### 6.4 ClientTransport (业务层包装)

```python
class ClientTransport:
    """客户端业务包装器：持有 Channel 并提供便捷接口"""
    def __init__(self, channel: IChannel):
        self.channel = channel
        self.pipeline = channel.pipeline

    async def send(self, msg: Message):
        """发送消息（异步）"""
        # 可以内部做一些协议转换或同步等待逻辑
        await self.channel.send(msg)

    def add_handler(self, handler: IMessageHandler):
        """允许用户注册自定义拦截器"""
        self.pipeline.add_last(handler)
```

---

## 7. 集成与使用 (Bootstrap)

### 7.1 本地同进程集成
```python
# 1. 创建物理通道对（对称初始化）
agent_ch, client_ch = ProcessorChannel.pair()

# 2. Agent 侧逻辑装配
context = AgentTransportContext()
agent_ch.pipeline.add_last(MessageDecoder())
agent_ch.pipeline.add_last(AgentExecuteHandler(context))

agent = MyAgent(context) # Agent 通过 Context 交互

# 3. Client 侧逻辑装配
client = ClientTransport(client_ch)
client.add_handler(LoggingHandler()) # 客户端也可以有自己的 Pipeline

# 4. 启动业务循环
await asyncio.gather(agent.run(), ...)
```
