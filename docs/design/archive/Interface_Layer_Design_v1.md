# 接口层设计 v1.0

> 本文档定义框架的完整接口层，回答：
> - 框架提供什么能力？
> - 开发者需要实现什么？
> - 扩展点在哪里？

---

## 一、接口全景图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DARE Framework                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Core Interfaces (框架提供)                     │    │
│  │                                                                   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │    │
│  │  │ IRuntime    │  │ IEventLog   │  │ IPolicy     │              │    │
│  │  │ (执行引擎)   │  │ (事件日志)   │  │ (策略引擎)  │              │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │    │
│  │                                                                   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │    │
│  │  │IToolRuntime │  │ IContext    │  │ IValidator  │              │    │
│  │  │ (工具门禁)   │  │ (上下文)    │  │ (验证器)    │              │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 Extension Interfaces (开发者实现)                 │    │
│  │                                                                   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │    │
│  │  │ ITool       │  │ ISkill      │  │ IMemory     │              │    │
│  │  │ (工具)      │  │ (技能)      │  │ (记忆)      │              │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │    │
│  │                                                                   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │    │
│  │  │IModelAdapter│  │ IVerifier   │  │ IHook       │              │    │
│  │  │ (模型适配)   │  │ (验证器)    │  │ (生命周期)  │              │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Agent (开发者组装)                             │    │
│  │                                                                   │    │
│  │     Agent = Runtime + Tools + Skills + Memory + Model            │    │
│  │                                                                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、接口分类

### 2.1 核心接口（Core Interfaces）

**框架提供默认实现，开发者可以替换但通常不需要。**

| 接口 | 职责 | 默认实现 | 可替换场景 |
|-----|-----|---------|-----------|
| `IRuntime` | 执行引擎，编排三层循环 | `AgentRuntime` | 需要自定义执行流程 |
| `IEventLog` | 事件日志，append-only | `LocalEventLog` | 需要分布式存储 |
| `IPolicyEngine` | 策略检查 | `PolicyEngine` | 需要自定义策略 |
| `IToolRuntime` | 工具执行门禁 | `ToolRuntime` | 通常不需要替换 |
| `IContextAssembler` | 上下文装配 | `ContextAssembler` | 需要自定义装配策略 |

### 2.2 扩展接口（Extension Interfaces）

**开发者必须或可选实现的接口。**

| 接口 | 职责 | 必须实现? | 说明 |
|-----|-----|----------|------|
| `ITool` | 定义一个工具 | 是（至少1个） | 框架提供基础工具集 |
| `ISkill` | 定义一个技能 | 否 | 可选，用于复杂任务分解 |
| `IMemory` | 记忆能力 | 否 | 可选，框架提供默认实现 |
| `IModelAdapter` | 模型适配 | 是（1个） | 框架提供 Claude/GPT 适配器 |
| `IVerifier` | 自定义验证 | 否 | 可选，扩展验证能力 |
| `IHook` | 生命周期钩子 | 否 | 可选，用于观测和扩展 |

### 2.3 组合接口（Composite）

| 接口 | 职责 | 说明 |
|-----|-----|------|
| `IAgent` | Agent 的完整定义 | 包含所有能力的组合 |
| `IToolkit` | 工具集合 | 一组相关工具的打包 |
| `ISkillPack` | 技能包 | 一组相关技能的打包 |

---

## 三、核心接口定义

### 3.1 IRuntime - 执行引擎

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator

class IRuntime(ABC):
    """
    执行引擎接口
    负责编排三层循环：Session → Milestone → Tool
    """

    @abstractmethod
    async def run(self, task: Task) -> RunResult:
        """
        执行任务（完整流程）

        Args:
            task: 任务定义

        Returns:
            RunResult: 执行结果
        """
        pass

    @abstractmethod
    async def run_stream(self, task: Task) -> AsyncIterator[RunEvent]:
        """
        流式执行任务（可观测）

        Yields:
            RunEvent: 执行过程中的事件
        """
        pass

    @abstractmethod
    async def resume(self, checkpoint_id: str) -> RunResult:
        """
        从检查点恢复执行

        Args:
            checkpoint_id: 检查点 ID
        """
        pass

    @abstractmethod
    async def cancel(self, run_id: str) -> None:
        """取消执行"""
        pass
```

### 3.2 IEventLog - 事件日志

```python
class IEventLog(ABC):
    """
    事件日志接口
    特点：append-only, hash chain, 可审计
    """

    @abstractmethod
    async def append(self, event: Event) -> str:
        """
        追加事件（唯一的写入方式）

        Returns:
            event_id: 事件ID
        """
        pass

    @abstractmethod
    async def get(self, event_id: str) -> Optional[Event]:
        """获取单个事件"""
        pass

    @abstractmethod
    async def query(
        self,
        run_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Event]:
        """查询事件"""
        pass

    @abstractmethod
    async def export(self, run_id: str) -> AsyncIterator[Event]:
        """导出运行的所有事件（用于审计）"""
        pass

    @abstractmethod
    async def verify_chain(self, start: str, end: str) -> VerifyResult:
        """验证哈希链完整性"""
        pass

    # 注意：没有 update() 和 delete() 方法
```

### 3.3 IToolRuntime - 工具执行门禁

```python
class IToolRuntime(ABC):
    """
    工具执行运行时
    所有工具调用必须经过这里
    职责：policy check → approval → execute → audit
    """

    @abstractmethod
    async def invoke(
        self,
        tool_name: str,
        input: dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """
        调用工具

        这是唯一的工具调用入口
        会自动：
        1. 从 Registry 获取工具契约
        2. 检查策略
        3. 检查审批（如需要）
        4. 执行工具
        5. 生成证据
        6. 写入审计日志
        """
        pass

    @abstractmethod
    async def invoke_batch(
        self,
        calls: list[ToolCall],
        context: ExecutionContext,
    ) -> list[ToolResult]:
        """
        批量调用工具（并行执行）
        用于独立的工具调用
        """
        pass

    @abstractmethod
    def register(self, tool: ITool) -> None:
        """注册工具"""
        pass

    @abstractmethod
    def list_tools(self) -> list[ToolSummary]:
        """列出可用工具"""
        pass
```

---

## 四、扩展接口定义

### 4.1 ITool - 工具接口

```python
class ITool(ABC):
    """
    工具接口
    开发者实现此接口来定义自己的工具
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（给 LLM 看的）"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """输入参数的 JSON Schema"""
        pass

    @property
    @abstractmethod
    def output_schema(self) -> dict:
        """输出的 JSON Schema"""
        pass

    @property
    def risk_level(self) -> RiskLevel:
        """风险级别，默认 READ_ONLY"""
        return RiskLevel.READ_ONLY

    @property
    def requires_approval(self) -> bool:
        """是否需要审批，默认 False"""
        return False

    @property
    def timeout_seconds(self) -> int:
        """超时时间，默认 30 秒"""
        return 30

    @property
    def produces_assertions(self) -> list[Assertion]:
        """产出断言（用于覆盖计算）"""
        return []

    @abstractmethod
    async def execute(
        self,
        input: dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        """
        执行工具

        Args:
            input: 输入参数（已经过消毒）
            context: 执行上下文

        Returns:
            工具输出

        Raises:
            ToolError: 工具执行失败
        """
        pass

    async def compensate(
        self,
        input: dict[str, Any],
        output: Any,
        context: ExecutionContext,
    ) -> None:
        """
        补偿操作（可选）
        只有 COMPENSATABLE 级别的工具需要实现
        """
        raise NotImplementedError("This tool does not support compensation")


# 使用示例
class ReadFileTool(ITool):
    """读取文件工具"""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"}
            },
            "required": ["path"]
        }

    @property
    def output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "size": {"type": "integer"}
            }
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.READ_ONLY

    async def execute(self, input: dict, context: ExecutionContext) -> dict:
        path = input["path"]
        content = await aiofiles.open(path).read()
        return {"content": content, "size": len(content)}
```

### 4.2 ISkill - 技能接口

```python
class ISkill(ABC):
    """
    技能接口
    技能 = 一组相关的工具调用 + 判断逻辑 + 完成条件

    与 Tool 的区别：
    - Tool：原子操作，单次调用
    - Skill：复合能力，可能包含多次工具调用和决策
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """技能名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """技能描述"""
        pass

    @property
    @abstractmethod
    def required_tools(self) -> list[str]:
        """此技能依赖的工具列表"""
        pass

    @property
    def done_predicate(self) -> DonePredicate:
        """完成条件"""
        return DonePredicate.DEFAULT

    @abstractmethod
    async def execute(
        self,
        task: SkillTask,
        tool_runtime: IToolRuntime,
        context: ExecutionContext,
    ) -> SkillResult:
        """
        执行技能

        技能内部可以：
        1. 多次调用工具
        2. 做出决策
        3. 处理错误和重试
        """
        pass


# 使用示例
class FixBugSkill(ISkill):
    """修复 Bug 的技能"""

    @property
    def name(self) -> str:
        return "fix_bug"

    @property
    def description(self) -> str:
        return "Analyze and fix a bug in the codebase"

    @property
    def required_tools(self) -> list[str]:
        return ["read_file", "write_file", "run_tests", "search_code"]

    async def execute(
        self,
        task: SkillTask,
        tool_runtime: IToolRuntime,
        context: ExecutionContext,
    ) -> SkillResult:
        # 1. 分析 bug 描述
        # 2. 搜索相关代码
        # 3. 读取文件
        # 4. 生成修复
        # 5. 写入文件
        # 6. 运行测试验证
        ...
```

### 4.3 IMemory - 记忆接口

```python
class IMemory(ABC):
    """
    记忆接口
    提供 Agent 的记忆能力

    记忆类型：
    - 短期记忆：当前会话内
    - 长期记忆：跨会话持久化
    - 情景记忆：特定事件的记录
    - 语义记忆：知识和事实
    """

    # === 短期记忆 ===

    @abstractmethod
    async def remember(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """记住某个信息"""
        pass

    @abstractmethod
    async def recall(self, key: str) -> Optional[Any]:
        """回忆某个信息"""
        pass

    @abstractmethod
    async def forget(self, key: str) -> None:
        """遗忘某个信息"""
        pass

    # === 长期记忆 ===

    @abstractmethod
    async def store(
        self,
        content: str,
        metadata: dict[str, Any],
        namespace: str = "default",
    ) -> str:
        """
        存储长期记忆

        Returns:
            memory_id: 记忆ID
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        namespace: str = "default",
        limit: int = 10,
    ) -> list[MemoryItem]:
        """
        搜索相关记忆（语义搜索）
        """
        pass

    # === 情景记忆 ===

    @abstractmethod
    async def record_episode(
        self,
        episode: Episode,
    ) -> str:
        """记录一个情景"""
        pass

    @abstractmethod
    async def recall_episodes(
        self,
        query: str,
        limit: int = 5,
    ) -> list[Episode]:
        """回忆相关情景"""
        pass

    # === 上下文窗口管理 ===

    @abstractmethod
    async def get_relevant_context(
        self,
        task: Task,
        budget_tokens: int,
    ) -> str:
        """
        获取与任务相关的记忆上下文
        在 token 预算内返回最相关的记忆
        """
        pass


@dataclass
class MemoryItem:
    """记忆项"""
    memory_id: str
    content: str
    metadata: dict[str, Any]
    relevance_score: float
    created_at: datetime


@dataclass
class Episode:
    """情景记忆"""
    episode_id: str
    description: str
    events: list[Event]
    outcome: str  # success / failure / partial
    lessons_learned: list[str]
    created_at: datetime
```

### 4.4 IHook - 生命周期钩子

```python
class IHook(ABC):
    """
    生命周期钩子接口
    用于在执行流程的关键点注入自定义逻辑
    """

    # === 运行级别钩子 ===

    async def on_run_start(self, task: Task, context: RunContext) -> None:
        """运行开始时"""
        pass

    async def on_run_end(self, result: RunResult, context: RunContext) -> None:
        """运行结束时"""
        pass

    # === 阶段级别钩子 ===

    async def on_phase_start(self, phase: RunPhase, state: RunState) -> None:
        """阶段开始时"""
        pass

    async def on_phase_end(self, phase: RunPhase, state: RunState) -> None:
        """阶段结束时"""
        pass

    # === 步骤级别钩子 ===

    async def before_step(self, step: ValidatedStep, context: ExecutionContext) -> None:
        """步骤执行前"""
        pass

    async def after_step(self, step: ValidatedStep, result: StepResult) -> None:
        """步骤执行后"""
        pass

    # === 工具级别钩子 ===

    async def before_tool(
        self,
        tool_name: str,
        input: dict,
        context: ExecutionContext,
    ) -> dict:
        """
        工具调用前
        可以修改输入
        """
        return input

    async def after_tool(
        self,
        tool_name: str,
        input: dict,
        result: ToolResult,
    ) -> ToolResult:
        """
        工具调用后
        可以修改输出
        """
        return result


# 使用示例：日志钩子
class LoggingHook(IHook):
    """记录所有执行过程的钩子"""

    def __init__(self, logger: Logger):
        self.logger = logger

    async def on_run_start(self, task: Task, context: RunContext) -> None:
        self.logger.info(f"Run started: {task.task_id}")

    async def before_tool(self, tool_name: str, input: dict, context: ExecutionContext) -> dict:
        self.logger.debug(f"Calling tool: {tool_name}")
        return input


# 使用示例：指标收集钩子
class MetricsHook(IHook):
    """收集执行指标的钩子"""

    async def after_step(self, step: ValidatedStep, result: StepResult) -> None:
        metrics.record_step_duration(
            step_id=step.step_id,
            duration=result.duration,
            success=result.success,
        )
```

### 4.5 IModelAdapter - 模型适配器

```python
class IModelAdapter(ABC):
    """
    模型适配器接口
    适配不同的 LLM 提供商
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称"""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """支持的模型列表"""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        tools: Optional[list[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        """
        生成响应

        Args:
            messages: 消息历史
            tools: 可用工具定义
            temperature: 温度
            max_tokens: 最大 token 数

        Returns:
            GenerateResult: 包含文本和工具调用
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[GenerateChunk]:
        """流式生成"""
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        生成嵌入向量（用于记忆的语义搜索）
        """
        pass


@dataclass
class GenerateResult:
    """生成结果"""
    content: str
    tool_calls: list[ToolCall]
    usage: TokenUsage
    stop_reason: str
```

---

## 五、Agent 组装

### 5.1 IAgent - Agent 完整接口

```python
class IAgent(ABC):
    """
    Agent 接口
    这是用户构建 Agent 的顶层接口
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent 名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent 描述"""
        pass

    @property
    @abstractmethod
    def tools(self) -> list[ITool]:
        """Agent 可用的工具"""
        pass

    @property
    def skills(self) -> list[ISkill]:
        """Agent 可用的技能"""
        return []

    @property
    def memory(self) -> Optional[IMemory]:
        """Agent 的记忆"""
        return None

    @property
    def hooks(self) -> list[IHook]:
        """Agent 的生命周期钩子"""
        return []

    @abstractmethod
    def get_model_adapter(self) -> IModelAdapter:
        """获取模型适配器"""
        pass


# Agent 构建器（简化组装）
class AgentBuilder:
    """Agent 构建器"""

    def __init__(self, name: str):
        self._name = name
        self._description = ""
        self._tools: list[ITool] = []
        self._skills: list[ISkill] = []
        self._memory: Optional[IMemory] = None
        self._hooks: list[IHook] = []
        self._model_adapter: Optional[IModelAdapter] = None

    def description(self, desc: str) -> "AgentBuilder":
        self._description = desc
        return self

    def with_tool(self, tool: ITool) -> "AgentBuilder":
        self._tools.append(tool)
        return self

    def with_tools(self, *tools: ITool) -> "AgentBuilder":
        self._tools.extend(tools)
        return self

    def with_skill(self, skill: ISkill) -> "AgentBuilder":
        self._skills.append(skill)
        return self

    def with_memory(self, memory: IMemory) -> "AgentBuilder":
        self._memory = memory
        return self

    def with_hook(self, hook: IHook) -> "AgentBuilder":
        self._hooks.append(hook)
        return self

    def with_model(self, adapter: IModelAdapter) -> "AgentBuilder":
        self._model_adapter = adapter
        return self

    def build(self) -> IAgent:
        """构建 Agent"""
        if not self._model_adapter:
            raise ValueError("Model adapter is required")
        if not self._tools:
            raise ValueError("At least one tool is required")

        return SimpleAgent(
            name=self._name,
            description=self._description,
            tools=self._tools,
            skills=self._skills,
            memory=self._memory,
            hooks=self._hooks,
            model_adapter=self._model_adapter,
        )


# 使用示例
coding_agent = (
    AgentBuilder("coding-agent")
    .description("A coding assistant that can read, write, and test code")
    .with_tools(
        ReadFileTool(),
        WriteFileTool(),
        RunTestsTool(),
        SearchCodeTool(),
    )
    .with_skill(FixBugSkill())
    .with_memory(VectorMemory(embedder=OpenAIEmbedder()))
    .with_hook(LoggingHook(logger))
    .with_model(ClaudeAdapter(model="claude-sonnet-4-20250514"))
    .build()
)
```

---

## 六、框架提供的默认实现

### 6.1 内置工具

| 工具 | 说明 | 风险级别 |
|-----|------|---------|
| `read_file` | 读取文件 | READ_ONLY |
| `write_file` | 写入文件 | IDEMPOTENT_WRITE |
| `list_directory` | 列出目录 | READ_ONLY |
| `search_code` | 搜索代码 | READ_ONLY |
| `run_command` | 运行命令 | NON_IDEMPOTENT |
| `run_tests` | 运行测试 | READ_ONLY |

### 6.2 内置记忆实现

| 实现 | 说明 | 适用场景 |
|-----|------|---------|
| `InMemoryMemory` | 内存记忆 | 开发/测试 |
| `VectorMemory` | 向量记忆 | 语义搜索 |
| `FileMemory` | 文件记忆 | 简单持久化 |
| `PostgresMemory` | PG 记忆 | 生产环境 |

### 6.3 内置模型适配器

| 适配器 | 支持模型 |
|-------|---------|
| `ClaudeAdapter` | claude-sonnet-4, claude-opus-4-5 |
| `OpenAIAdapter` | gpt-4o, gpt-4o-mini |
| `OllamaAdapter` | 本地模型 |

---

## 七、扩展点总结

| 扩展点 | 接口 | 何时扩展 |
|-------|------|---------|
| 添加新工具 | `ITool` | 需要新能力时 |
| 添加新技能 | `ISkill` | 需要复合能力时 |
| 自定义记忆 | `IMemory` | 需要特殊记忆策略时 |
| 自定义模型 | `IModelAdapter` | 使用新 LLM 时 |
| 自定义验证 | `IVerifier` | 需要特殊验证逻辑时 |
| 生命周期扩展 | `IHook` | 需要观测/修改执行流程时 |
| 自定义策略 | `IPolicyEngine` | 需要特殊权限控制时 |
| 自定义存储 | `IEventLog` | 需要分布式/云存储时 |

---

## 八、开发者快速上手

### 8.1 最小 Agent（只需 3 步）

```python
# 1. 选择或实现工具
from dare_framework.tools import ReadFileTool, WriteFileTool

# 2. 选择模型适配器
from dare_framework.models import ClaudeAdapter

# 3. 构建 Agent
agent = (
    AgentBuilder("my-agent")
    .with_tools(ReadFileTool(), WriteFileTool())
    .with_model(ClaudeAdapter())
    .build()
)

# 运行
result = await agent.run(Task(description="读取 README.md 并总结"))
```

### 8.2 添加自定义工具

```python
class MyCustomTool(ITool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Does something useful"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {"param": {"type": "string"}}}

    @property
    def output_schema(self) -> dict:
        return {"type": "object", "properties": {"result": {"type": "string"}}}

    async def execute(self, input: dict, context: ExecutionContext) -> dict:
        return {"result": f"Processed: {input['param']}"}

# 注册到 Agent
agent = AgentBuilder("my-agent").with_tool(MyCustomTool()).with_model(...).build()
```

---

*文档状态：接口设计 v1.0，待评审*
