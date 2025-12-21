# 框架对比分析：Pydantic AI

> 分析 Pydantic AI 的设计优势，取其精华，保持差异化。

---

## 一、Pydantic AI 的核心优势

### 1.1 设计哲学

```
Pydantic AI 的哲学："FastAPI 感觉"
├── 类型安全 → "if it compiles, it works"
├── 开发者体验 → IDE 自动补全、类型检查
├── 依赖注入 → 测试友好
└── 结构化输出 → Pydantic 模型验证
```

### 1.2 关键设计模式

#### 1. RunContext 依赖注入（非常优雅！）

```python
# Pydantic AI 的依赖注入模式
@dataclass
class SupportDependencies:
    customer_id: int
    db: DatabaseConn

@support_agent.tool
async def get_customer_info(ctx: RunContext[SupportDependencies]) -> str:
    # ctx.deps 有完整的类型支持！
    return await ctx.deps.db.get_customer(ctx.deps.customer_id)
```

**优点**：
- 类型安全的依赖访问
- 测试时可以轻松 mock
- 不需要在函数间传递大量参数

#### 2. 结构化输出

```python
class SupportOutput(BaseModel):
    support_advice: str = Field(description='Advice returned to the customer')
    block_card: bool = Field(description="Whether to block the customer's card")
    risk: int = Field(description='Risk level of query', ge=0, le=10)

agent = Agent(output_type=SupportOutput)
result = await agent.run("...")
# result.output 有完整类型：SupportOutput
```

#### 3. Durable Execution（持久化执行）

```python
# 可以跨重启恢复的 agent
class BaseStatePersistence:
    async def snapshot_node(state, next_node) -> None
    async def snapshot_end(state, end) -> None
    async def load_next() -> NodeSnapshot | None
    def record_run(snapshot_id) -> AsyncContextManager
```

---

## 二、接口对照分析

### 2.1 接口映射表

| Pydantic AI | DARE Framework | 分析 |
|-------------|---------------|------|
| `AbstractAgent` | `IAgent` | 类似，但 PA 有更好的泛型支持 |
| `Model` | `IModelAdapter` | 类似 |
| `StreamedResponse` | `IStreamHandler`? | 我们缺少流式响应抽象 |
| `RunContext` | **缺失！** | 应该学习这个依赖注入模式 |
| `AgentRun` | `IRuntime.run_stream` | 类似的迭代执行 |
| `AbstractToolset` | `IToolkit` | PA 的更完善（支持过滤、前缀） |
| `Provider` | `IModelAdapter` | 我们合并了 Provider 和 Model |
| `UIAdapter` | **缺失！** | 我们没有 UI 协议抽象 |
| `AbstractBuiltinTool` | `ITool` | 类似 |
| `BaseStatePersistence` | `IEventLog` + `ICheckpoint` | 我们分成两个接口 |
| `StateHandler` | 部分在 `ICheckpoint` | 我们的更偏向审计 |

### 2.2 我们缺失的关键接口

```
1. RunContext / ExecutionContext（依赖注入）
   → 我们有 ExecutionContext 但没有泛型依赖注入

2. StreamedResponse（流式响应抽象）
   → 我们只有同步结果

3. UIAdapter（UI 协议适配）
   → 我们没有考虑 UI 层

4. 结构化输出类型
   → 我们的 output 是 Any，没有类型验证
```

---

## 三、应该学习的设计

### 3.1 RunContext 依赖注入

**Pydantic AI 的方式**：
```python
@dataclass
class Deps:
    db: Database
    user_id: str

agent = Agent(deps_type=Deps)

@agent.tool
async def query(ctx: RunContext[Deps]) -> str:
    return await ctx.deps.db.query(ctx.deps.user_id)

# 运行时注入依赖
result = await agent.run("...", deps=Deps(db=db, user_id="123"))
```

**我们应该改进的**：
```python
# 当前的 DARE 方式
async def execute(self, input: dict, context: ExecutionContext) -> Any:
    # context 没有泛型，类型信息丢失

# 改进后
@dataclass
class AgentDeps:
    workspace: Path
    db: Database

class CodingAgent(Agent[AgentDeps]):  # 泛型！
    @tool
    async def read_file(self, ctx: RunContext[AgentDeps], path: str) -> str:
        # ctx.deps.workspace 有完整类型！
        full_path = ctx.deps.workspace / path
        return full_path.read_text()
```

### 3.2 结构化输出类型

**Pydantic AI 的方式**：
```python
class TaskOutput(BaseModel):
    result: str
    files_modified: list[str]
    tests_passed: bool

agent = Agent(output_type=TaskOutput)
result = await agent.run("...")
# result.output: TaskOutput（有类型！）
```

**我们应该改进的**：
```python
# 当前的 DARE 方式
class RunResult:
    output: Any  # 没有类型

# 改进后
class RunResult(Generic[T]):
    output: T  # 有类型！

agent = Agent[Deps, TaskOutput](...)
result: RunResult[TaskOutput] = await agent.run(...)
```

### 3.3 Toolset 增强

**Pydantic AI 的 Toolset 特性**：
```python
class AbstractToolset:
    @property
    def id(self) -> str  # 唯一标识（用于持久化）

    async def __aenter__(self)  # 支持连接管理
    async def __aexit__(self)

    async def get_tools(ctx) -> dict[str, Tool]  # 动态工具列表
    async def call_tool(name, args, ctx, tool)  # 调用工具

# 支持过滤、前缀、重命名
toolset.filter(lambda t: t.risk_level == "low")
toolset.prefix("file_")
toolset.rename({"read": "read_file"})
```

**我们应该改进的**：
```python
class IToolkit:
    @property
    def id(self) -> str  # 添加：用于持久化标识

    async def __aenter__(self) -> Self  # 添加：连接管理
    async def __aexit__(self, *args)

    def filter(self, predicate) -> IToolkit  # 添加：过滤
    def prefix(self, prefix: str) -> IToolkit  # 添加：前缀
```

### 3.4 流式响应抽象

**Pydantic AI 的 StreamedResponse**：
```python
class StreamedResponse:
    async def __aiter__(self) -> AsyncIterator[ModelResponseStreamEvent]
    def get(self) -> ModelResponse  # 获取当前累积结果
    def usage(self) -> RequestUsage  # 当前 token 使用

    # 自动处理：
    # - 部分响应累积
    # - Final result 检测
    # - PartStart/PartEnd 事件
```

**我们应该添加的**：
```python
class IStreamedResponse:
    async def __aiter__(self) -> AsyncIterator[StreamEvent]
    def get_partial(self) -> PartialResult  # 当前部分结果
    def get_final(self) -> Result  # 最终结果
    def usage(self) -> TokenUsage  # token 使用统计
```

---

## 四、应该保持不同的设计

### 4.1 信任边界（DARE 独有）

```
Pydantic AI：没有信任边界概念
├── 工具输出直接使用
├── LLM 输出直接作为结果
└── 没有安全关键字段派生

DARE Framework：信任边界是核心
├── LLM 输出不可信
├── 安全关键字段从 Registry 派生
├── 工具调用必须经过门禁
└── 所有操作可审计
```

**我们应该保持**：`TrustBoundary`, `PolicyEngine`, `IToolRuntime` 门禁

### 4.2 审计日志（DARE 增强）

```
Pydantic AI 的 BaseStatePersistence：
├── 主要用于恢复执行
├── snapshot_node / snapshot_end
└── 目的是持久化执行

DARE 的 EventLog：
├── 不仅用于恢复，还用于审计
├── Hash chain 防篡改
├── WORM 存储
├── 证据链
└── 金融级合规
```

**我们应该保持**：`IEventLog` 的 append-only + hash chain + 审计特性

### 4.3 工具风险级别（DARE 独有）

```
Pydantic AI：
├── 工具就是工具，没有风险分类
└── 没有审批机制

DARE：
├── READ_ONLY / IDEMPOTENT_WRITE / NON_IDEMPOTENT / COMPENSATABLE
├── 高风险工具需要审批
└── 补偿操作支持
```

**我们应该保持**：`ToolRiskLevel`, `requires_approval`, `compensate()`

### 4.4 验证闭环（DARE 独有）

```
Pydantic AI：输出验证是 Pydantic 模型验证
DARE：每个安全机制都有完整闭环
      输入 → 不可变事实 → 系统强制 → 证据 → 复验
```

**我们应该保持**：五个可验证闭环的设计

---

## 五、综合建议

### 5.1 应该添加的接口

| 接口 | 来源 | 说明 |
|-----|------|------|
| `RunContext[T]` | Pydantic AI | 泛型依赖注入上下文 |
| `IStreamedResponse` | Pydantic AI | 流式响应抽象 |
| `IUIAdapter` | Pydantic AI | UI 协议适配 |
| 结构化输出泛型 | Pydantic AI | `Agent[Deps, Output]` |

### 5.2 应该增强的接口

| 接口 | 增强内容 | 来源 |
|-----|---------|------|
| `IToolkit` | 添加 `id`, `filter()`, `prefix()` | Pydantic AI |
| `ExecutionContext` | 改为泛型 `RunContext[T]` | Pydantic AI |
| `ICheckpoint` | 学习 `BaseStatePersistence` 的 API | Pydantic AI |

### 5.3 应该保持的设计

| 设计 | 原因 |
|-----|------|
| 信任边界 | 安全核心，Pydantic AI 没有 |
| 审计日志 | 合规要求，超越简单的状态恢复 |
| 工具风险级别 | 安全分类，Pydantic AI 没有 |
| 策略引擎 | 权限控制，Pydantic AI 没有 |
| 验证闭环 | 金融级要求 |

---

## 六、修正后的接口设计

### 6.1 新增：RunContext 泛型依赖注入

```python
from typing import Generic, TypeVar

DepsT = TypeVar("DepsT")

@dataclass
class RunContext(Generic[DepsT]):
    """
    运行上下文
    学习自 Pydantic AI 的依赖注入模式
    """
    # 依赖注入
    deps: DepsT

    # 运行标识
    run_id: str
    step_id: str

    # DARE 特有：信任边界信息
    trust_level: TrustLevel
    agent_id: str
    task_id: str

    # DARE 特有：策略上下文
    policy_context: PolicyContext

    # 便捷方法
    async def get_memory(self) -> IMemory:
        """获取记忆接口"""
        return self.deps.memory if hasattr(self.deps, 'memory') else None

    def log_event(self, event_type: str, payload: dict) -> None:
        """记录事件到 EventLog"""
        # 自动注入 run_id, step_id, agent_id 等
        pass


# 使用示例
@dataclass
class CodingAgentDeps:
    workspace: Path
    db: Database
    memory: IMemory

class CodingAgent(Agent[CodingAgentDeps, TaskOutput]):
    @tool
    async def read_file(self, ctx: RunContext[CodingAgentDeps], path: str) -> str:
        # ctx.deps.workspace 有完整类型！
        full_path = ctx.deps.workspace / path
        return full_path.read_text()
```

### 6.2 新增：结构化输出泛型

```python
OutputT = TypeVar("OutputT", bound=BaseModel)

class Agent(Generic[DepsT, OutputT]):
    """
    泛型 Agent
    DepsT: 依赖类型
    OutputT: 输出类型
    """

    def __init__(
        self,
        name: str,
        deps_type: type[DepsT],
        output_type: type[OutputT],
    ):
        self._deps_type = deps_type
        self._output_type = output_type

    async def run(
        self,
        task: Task,
        deps: DepsT,
    ) -> RunResult[OutputT]:
        """运行 Agent，返回类型化结果"""
        # 执行...
        # 输出会被验证为 OutputT
        pass


# 使用示例
class CodeFixOutput(BaseModel):
    success: bool
    files_modified: list[str]
    test_results: TestReport

agent = Agent[CodingAgentDeps, CodeFixOutput](
    name="coding-agent",
    deps_type=CodingAgentDeps,
    output_type=CodeFixOutput,
)

result = await agent.run(task, deps=CodingAgentDeps(...))
# result.output: CodeFixOutput（有类型！）
```

### 6.3 增强：IToolkit

```python
class IToolkit(ABC):
    """
    工具集接口
    增强自 Pydantic AI 的 AbstractToolset
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """
        工具集唯一标识
        用于持久化执行中识别工具集
        """
        pass

    # 异步上下文管理（连接管理）
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args) -> None:
        pass

    @abstractmethod
    async def get_tools(self, ctx: RunContext) -> dict[str, ITool]:
        """获取工具列表（可以是动态的）"""
        pass

    @abstractmethod
    async def call_tool(
        self,
        name: str,
        args: dict,
        ctx: RunContext,
    ) -> ToolResult:
        """调用工具"""
        pass

    # 工具集变换（来自 Pydantic AI）
    def filter(self, predicate: Callable[[ITool], bool]) -> "IToolkit":
        """过滤工具"""
        return FilteredToolkit(self, predicate)

    def prefix(self, prefix: str) -> "IToolkit":
        """添加工具名前缀"""
        return PrefixedToolkit(self, prefix)

    def rename(self, mapping: dict[str, str]) -> "IToolkit":
        """重命名工具"""
        return RenamedToolkit(self, mapping)
```

### 6.4 新增：IStreamedResponse

```python
class IStreamedResponse(ABC, Generic[OutputT]):
    """
    流式响应接口
    学习自 Pydantic AI
    """

    @abstractmethod
    def __aiter__(self) -> AsyncIterator[StreamEvent]:
        """迭代流式事件"""
        pass

    @abstractmethod
    def get_partial(self) -> PartialResult[OutputT]:
        """获取当前部分结果"""
        pass

    @abstractmethod
    def get_final(self) -> OutputT:
        """获取最终结果（流结束后）"""
        pass

    @abstractmethod
    def usage(self) -> TokenUsage:
        """获取 token 使用统计"""
        pass

    @abstractmethod
    def is_complete(self) -> bool:
        """是否已完成"""
        pass


@dataclass
class StreamEvent:
    """流式事件"""
    event_type: str  # text_delta, tool_call_start, tool_call_end, ...
    data: Any
    timestamp: datetime
```

---

## 七、最终接口全景（融合后）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DARE Framework v2                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Layer 1: Core Infrastructure（DARE 核心，保持）                         │
│  ─────────────────────────────────────────────────────────────────────  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ IRuntime    │  │ IEventLog   │  │IToolRuntime │  │ IPolicy     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│  ┌─────────────┐  ┌─────────────┐                                      │
│  │TrustBoundary│  │ IContext    │                                      │
│  └─────────────┘  └─────────────┘                                      │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Layer 2: Type-Safe Abstractions（学习自 Pydantic AI）                   │
│  ─────────────────────────────────────────────────────────────────────  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  RunContext[DepsT]        ← 新增：泛型依赖注入                    │   │
│  │  Agent[DepsT, OutputT]    ← 新增：泛型 Agent                     │   │
│  │  RunResult[OutputT]       ← 新增：泛型结果                       │   │
│  │  IStreamedResponse[T]     ← 新增：流式响应                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Layer 3: Pluggable Components（保持 + 增强）                            │
│  ─────────────────────────────────────────────────────────────────────  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  IModelAdapter       ← 保持                                      │   │
│  │  IToolkit            ← 增强：添加 id, filter, prefix              │   │
│  │  IMCPClient          ← 保持                                      │   │
│  │  IMemory             ← 保持                                      │   │
│  │  ISkill              ← 保持                                      │   │
│  │  IHook               ← 保持                                      │   │
│  │  IUIAdapter          ← 新增：UI 协议适配                          │   │
│  │  ICheckpoint         ← 增强：学习 BaseStatePersistence            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DARE 独有特性（保持差异化）                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  信任边界        TrustBoundary, LLM 输出不可信                    │   │
│  │  审计日志        EventLog + Hash Chain + WORM                    │   │
│  │  工具风险级别    ToolRiskLevel + 审批机制                         │   │
│  │  策略引擎        PolicyEngine                                    │   │
│  │  验证闭环        五个可验证闭环                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 八、总结

### 从 Pydantic AI 学习

| 学习点 | 具体内容 | 优先级 |
|-------|---------|--------|
| 依赖注入 | `RunContext[T]` 泛型上下文 | P0 |
| 结构化输出 | `Agent[Deps, Output]` 泛型 | P0 |
| 流式响应 | `IStreamedResponse` | P1 |
| 工具集增强 | `id`, `filter()`, `prefix()` | P1 |
| UI 适配 | `IUIAdapter` | P2 |
| 持久化增强 | 学习 `BaseStatePersistence` API | P1 |

### 保持差异化

| DARE 特有 | Pydantic AI 对应 | 为什么保持 |
|----------|-----------------|-----------|
| 信任边界 | 无 | 安全核心 |
| EventLog 审计 | 简单持久化 | 合规要求 |
| 工具风险级别 | 无 | 安全分类 |
| 策略引擎 | 无 | 权限控制 |
| 验证闭环 | 无 | 金融级可验证 |

---

*文档状态：框架对比分析完成*
