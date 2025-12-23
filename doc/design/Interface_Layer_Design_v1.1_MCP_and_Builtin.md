# 接口层设计 v1.1 - MCP 支持与内置实现

> 本文档补充 v1.0 遗漏的内容：
> 1. MCP (Model Context Protocol) 支持
> 2. 内置实现 vs 扩展接口的平衡
> 3. 与 AgentScope 的对比分析

---

## 一、修正后的接口分层

### 1.1 三层模型

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  Layer 1: Core Infrastructure（框架核心，通常不替换）                    │
│  ─────────────────────────────────────────────────────────────────────  │
│  这些是框架的骨架，提供安全性和可审计性保证。                             │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ IRuntime    │  │ IEventLog   │  │IToolRuntime │  │IPolicyEngine│    │
│  │ 执行引擎    │  │ 事件日志    │  │ 工具门禁    │  │ 策略引擎    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                    │
│  │TrustBoundary│  │ IContextAsse│  │ IValidator  │                    │
│  │             │  │ mbler       │  │ 统一验证    │                    │
│  │ 信任边界    │  │ 上下文装配  │  │             │                    │
│  └─────────────┘  └─────────────┘  └─────────────┘                    │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                    │
│  │IPlanGenerator│  │ IRemediator │  │ISkillRegistry│                   │
│  │  Plan 生成  │  │  反思分析   │  │  Skill 管理 │                   │
│  └─────────────┘  └─────────────┘  └─────────────┘                    │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Layer 2: Pluggable Components（可插拔，框架提供默认实现）               │
│  ─────────────────────────────────────────────────────────────────────  │
│  这些有抽象接口 + 框架内置实现。开发者可以用内置的，也可以自定义。        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  IModelAdapter                                                   │   │
│  │  ├── ClaudeAdapter      ✅ 内置                                  │   │
│  │  ├── OpenAIAdapter      ✅ 内置                                  │   │
│  │  ├── OllamaAdapter      ✅ 内置                                  │   │
│  │  └── 开发者自定义...                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  IMemory                                                         │   │
│  │  ├── InMemoryMemory     ✅ 内置（开发/测试用）                    │   │
│  │  ├── VectorMemory       ✅ 内置（语义搜索）                       │   │
│  │  ├── FileMemory         ✅ 内置（简单持久化）                     │   │
│  │  └── 开发者自定义...                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ITool / IToolkit（Execute Tools）                               │   │
│  │  ├── 文件操作工具       ✅ 内置                                  │   │
│  │  │   ├── ReadFileTool                                            │   │
│  │  │   ├── WriteFileTool                                           │   │
│  │  │   └── SearchCodeTool                                          │   │
│  │  ├── 命令执行工具       ✅ 内置                                  │   │
│  │  │   ├── RunCommandTool                                          │   │
│  │  │   └── RunTestsTool                                            │   │
│  │  ├── MCP 工具           ✅ 内置（重要！）                         │   │
│  │  │   └── MCPToolkit                                              │   │
│  │  └── 开发者自定义...                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ISkill（Plan Tools）                                             │   │
│  │  ├── （框架可能提供一些通用技能）                                 │   │
│  │  └── 主要由开发者定义业务相关技能                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  IHook                                                           │   │
│  │  ├── LoggingHook        ✅ 内置                                  │   │
│  │  ├── MetricsHook        ✅ 内置                                  │   │
│  │  └── 开发者自定义...                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Layer 3: Agent Composition（组装层）                                    │
│  ─────────────────────────────────────────────────────────────────────  │
│  开发者使用 AgentBuilder 组装以上组件。                                  │
│                                                                         │
│  agent = AgentBuilder("my-agent")                                       │
│      .with_model(ClaudeAdapter())      # 用内置的                       │
│      .with_tools(ReadFileTool(), ...)  # 用内置的                       │
│      .with_skills(FixFailingTest())    # Plan Tools / Skills            │
│      .with_mcp("filesystem", "github") # MCP 服务器                     │
│      .with_memory(VectorMemory())      # 用内置的                       │
│      .build()                                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、MCP (Model Context Protocol) 支持

### 2.1 为什么需要 MCP

```
传统方式：每个工具单独实现
├── ReadFileTool（自己写）
├── WriteFileTool（自己写）
├── GitTool（自己写）
└── ...（每个都要写）

MCP 方式：工具作为服务
├── MCP Server: filesystem（提供文件操作）
├── MCP Server: git（提供 Git 操作）
├── MCP Server: github（提供 GitHub API）
└── Agent 通过标准协议调用
```

**好处**：
1. 工具可复用（一个 MCP Server 多个 Agent 共享）
2. 语言无关（MCP Server 可以用任何语言实现）
3. 生态丰富（已有很多开源 MCP Server）

### 2.2 MCP 接口设计

```python
class IMCPClient(ABC):
    """
    MCP 客户端接口
    用于连接和调用 MCP 服务器
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """MCP 服务器名称"""
        pass

    @property
    @abstractmethod
    def transport(self) -> str:
        """传输方式：stdio | sse | websocket"""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """连接到 MCP 服务器"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def list_tools(self) -> list[ToolDefinition]:
        """列出 MCP 服务器提供的工具"""
        pass

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
        context: ExecutionContext,
    ) -> ToolResult:
        """调用 MCP 工具"""
        pass

    @abstractmethod
    async def list_resources(self) -> list[Resource]:
        """列出 MCP 服务器提供的资源"""
        pass

    @abstractmethod
    async def read_resource(self, uri: str) -> ResourceContent:
        """读取资源"""
        pass


# 框架内置实现
class StdioMCPClient(IMCPClient):
    """
    Stdio 传输的 MCP 客户端
    用于本地进程通信
    """
    transport = "stdio"

    def __init__(self, name: str, command: list[str]):
        self.name = name
        self._command = command
        self._process = None

    async def connect(self):
        self._process = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )

    # ... 实现其他方法


class SSEMCPClient(IMCPClient):
    """
    SSE 传输的 MCP 客户端
    用于远程服务器通信
    """
    transport = "sse"

    def __init__(self, name: str, url: str):
        self.name = name
        self._url = url

    # ... 实现其他方法
```

### 2.3 MCPToolkit - MCP 工具集成

```python
class MCPToolkit(IToolkit):
    """
    MCP 工具包
    将 MCP 服务器的工具暴露为框架工具
    """

    def __init__(self, clients: list[IMCPClient]):
        self._clients = {c.name: c for c in clients}
        self._tools: dict[str, MCPTool] = {}

    async def initialize(self) -> None:
        """
        初始化：连接所有 MCP 服务器并收集工具
        """
        for name, client in self._clients.items():
            await client.connect()

            # 获取该服务器的所有工具
            tools = await client.list_tools()
            for tool_def in tools:
                # 将 MCP 工具包装为框架工具
                mcp_tool = MCPTool(
                    client=client,
                    tool_def=tool_def,
                )
                # 使用 "server:tool" 格式命名，避免冲突
                full_name = f"{name}:{tool_def.name}"
                self._tools[full_name] = mcp_tool

    def list_tools(self) -> list[ITool]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[ITool]:
        return self._tools.get(name)


class MCPTool(ITool):
    """
    单个 MCP 工具的包装
    将 MCP 工具适配为框架的 ITool 接口
    """

    def __init__(self, client: IMCPClient, tool_def: ToolDefinition):
        self._client = client
        self._def = tool_def

    @property
    def name(self) -> str:
        return f"{self._client.name}:{self._def.name}"

    @property
    def description(self) -> str:
        return self._def.description

    @property
    def input_schema(self) -> dict:
        return self._def.input_schema

    @property
    def risk_level(self) -> ToolRiskLevel:
        # MCP 工具默认需要更高的警惕
        # 可以通过配置覆盖
        return ToolRiskLevel.IDEMPOTENT_WRITE

    async def execute(self, input: dict, context: ExecutionContext) -> Any:
        return await self._client.call_tool(
            tool_name=self._def.name,
            arguments=input,
            context=context,
        )
```

### 2.4 使用 MCP 的 Agent

```python
# 方式 1：直接使用 MCPToolkit
agent = (
    AgentBuilder("coding-agent")
    .with_model(ClaudeAdapter())
    .with_mcp_servers(
        StdioMCPClient("filesystem", ["npx", "@anthropic/mcp-filesystem"]),
        StdioMCPClient("git", ["npx", "@anthropic/mcp-git"]),
    )
    .build()
)

# 方式 2：混合使用内置工具和 MCP
agent = (
    AgentBuilder("coding-agent")
    .with_model(ClaudeAdapter())
    .with_tools(
        ReadFileTool(),      # 内置工具
        WriteFileTool(),     # 内置工具
    )
    .with_mcp_servers(
        StdioMCPClient("github", ["npx", "@anthropic/mcp-github"]),
    )
    .build()
)
```

---

## 三、与 AgentScope 的对比

### 3.1 接口对照表

| AgentScope | DARE Framework | 说明 |
|------------|---------------|------|
| `AgentBase` | `IAgent` | Agent 基类 |
| `Msg` | `Message` | 消息结构 |
| `Toolkit` | `IToolkit` + `MCPToolkit` | 工具管理 |
| `StateModule` | `ICheckpoint` | 状态序列化 |
| `ChatModelBase` | `IModelAdapter` | 模型适配 |
| `MemoryBase` | `IMemory` | 记忆接口 |
| `LongTermMemoryBase` | `IMemory.store/search` | 长期记忆 |
| `MCPClientBase` | `IMCPClient` | MCP 客户端 |
| `ReaderBase` | `IDocumentReader` | RAG 文档读取 |
| `VDBStoreBase` | `IVectorStore` | 向量存储 |
| `KnowledgeBase` | `IKnowledgeBase` | 知识库 |
| `FormatterBase` | `IPromptFormatter` | Prompt 格式化 |
| `TokenCounterBase` | `ITokenCounter` | Token 计数 |
| - | `IEventLog` | **DARE 特有**：审计日志 |
| - | `TrustBoundary` | **DARE 特有**：信任边界 |
| - | `IPolicyEngine` | **DARE 特有**：策略引擎 |
| - | `IPlanGenerator` | **DARE 特有**：计划生成 |
| - | `IRemediator` | **DARE 特有**：反思生成 |
| - | `ISkillRegistry` | **DARE 特有**：Skill 注册 |

### 3.2 我们应该学习的

1. **StateModule 模式** - 嵌套状态序列化
   ```python
   # AgentScope 的 StateModule 支持嵌套
   agent.state_dict()  # 自动包含所有子模块的状态
   agent.load_state_dict(state)  # 自动恢复
   ```
   → 我们的 `ICheckpoint` 也应该支持

2. **Toolkit 的分组管理** - AgentScope 支持工具分组
   ```python
   toolkit.activate_group("file_tools")
   toolkit.deactivate_group("dangerous_tools")
   ```
   → 我们可以学习这个设计

3. **FormatterBase** - Prompt 格式化抽象
   → 不同模型有不同的消息格式，需要抽象

4. **Evaluator 系统** - 评估框架
   → 我们目前没有，后期可以加

### 3.3 我们应该不同的

1. **信任边界是核心** - DARE 的 `TrustBoundary` 是独特设计
   - AgentScope 没有这个概念
   - 我们强调 LLM 输出不可信

2. **EventLog 是核心** - 所有操作必须可审计
   - AgentScope 的 StateModule 主要是状态恢复
   - 我们还需要审计和证据链

3. **PolicyEngine** - 策略强制
   - AgentScope 没有这个层
   - 我们需要权限控制

4. **验证闭环** - 每个安全机制都要可验证
   - 这是金融级场景的要求

---

## 四、修正后的内置实现列表

### 4.1 模型适配器

| 实现 | 状态 | 说明 |
|-----|------|------|
| `ClaudeAdapter` | ✅ 内置 | Anthropic Claude API |
| `OpenAIAdapter` | ✅ 内置 | OpenAI API |
| `OllamaAdapter` | ✅ 内置 | 本地模型 |
| `AzureOpenAIAdapter` | 可选 | Azure 部署 |
| `BedrockAdapter` | 可选 | AWS Bedrock |

### 4.2 记忆实现

| 实现 | 状态 | 说明 |
|-----|------|------|
| `InMemoryMemory` | ✅ 内置 | 开发/测试用 |
| `VectorMemory` | ✅ 内置 | 语义搜索 |
| `FileMemory` | ✅ 内置 | 简单持久化 |
| `PostgresMemory` | 可选 | 生产环境 |
| `RedisMemory` | 可选 | 分布式 |

### 4.3 工具实现

| 实现 | 状态 | 说明 |
|-----|------|------|
| `ReadFileTool` | ✅ 内置 | 读取文件 |
| `WriteFileTool` | ✅ 内置 | 写入文件 |
| `SearchCodeTool` | ✅ 内置 | 代码搜索 |
| `RunCommandTool` | ✅ 内置 | 运行命令 |
| `RunTestsTool` | ✅ 内置 | 运行测试 |
| `MCPToolkit` | ✅ 内置 | MCP 工具集成 |

### 4.4 MCP 客户端

| 实现 | 状态 | 说明 |
|-----|------|------|
| `StdioMCPClient` | ✅ 内置 | 本地进程 |
| `SSEMCPClient` | ✅ 内置 | HTTP SSE |
| `WebSocketMCPClient` | 可选 | WebSocket |

### 4.5 钩子实现

| 实现 | 状态 | 说明 |
|-----|------|------|
| `LoggingHook` | ✅ 内置 | 日志记录 |
| `MetricsHook` | ✅ 内置 | 指标收集 |
| `TracingHook` | 可选 | OpenTelemetry |

---

## 五、易用性与扩展性的平衡

### 5.1 设计原则

```
1. 开箱即用
   → 新手可以用内置实现快速开始
   → 不需要实现任何接口

2. 渐进式扩展
   → 需要自定义时，只扩展需要的部分
   → 其他部分继续用内置

3. 完全可替换
   → 高级用户可以替换任何组件
   → 接口足够抽象
```

### 5.2 三种使用模式

```python
# 模式 1：开箱即用（零配置）
agent = AgentBuilder.quick_start(
    name="my-agent",
    model="claude-sonnet",
)

# 模式 2：选择性配置（混合使用）
agent = (
    AgentBuilder("my-agent")
    .with_model(ClaudeAdapter())      # 用内置的
    .with_tools(ReadFileTool())       # 用内置的
    .with_memory(MyCustomMemory())    # 自定义
    .build()
)

# 模式 3：完全自定义（高级用户）
agent = (
    AgentBuilder("my-agent")
    .with_model(MyModelAdapter())
    .with_tools(MyTool1(), MyTool2())
    .with_memory(MyMemory())
    .with_hook(MyHook())
    .with_runtime(MyRuntime())
    .build()
)
```

### 5.3 接口文档清晰度

每个接口都应该有：
1. **接口定义** - 抽象方法
2. **内置实现列表** - 开发者知道有什么可用
3. **扩展指南** - 如何自定义
4. **使用示例** - 代码示例

---

## 六、总结

### 6.1 关键修正

| 原设计 | 修正后 |
|-------|-------|
| Extension = 开发者必须实现 | Extension = 可扩展点，框架提供默认实现 |
| 没有 MCP 支持 | 添加 `IMCPClient` 和 `MCPToolkit` |
| 没有内置工具列表 | 明确列出所有内置实现 |
| 没有使用模式 | 定义三种使用模式（开箱即用/混合/完全自定义）|

### 6.2 与 AgentScope 的差异

| 方面 | AgentScope | DARE |
|-----|-----------|------|
| 核心关注 | 通用性、易用性 | 安全性、可审计性 |
| 信任模型 | 无 | LLM 不可信，信任边界 |
| 审计 | StateModule（状态恢复）| EventLog（审计追踪）|
| 策略 | 无 | PolicyEngine |
| MCP | ✅ 支持 | ✅ 支持（新增）|

---

*文档状态：v1.1，补充 MCP 和内置实现*
