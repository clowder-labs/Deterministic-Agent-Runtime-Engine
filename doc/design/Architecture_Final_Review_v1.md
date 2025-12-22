# DARE（Deterministic Agent Runtime Engine） Framework 架构终稿评审

> 综合 AgentScope 和 Pydantic AI 的分析，确定最终接口架构设计。

---

## 一、最终架构总览

```
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                           DARE Framework 架构全景                                  ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                    ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ Layer 1: Core Infrastructure（框架核心，通常不替换）                         ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        ┃ ║
║  ┃  │ IRuntime    │  │ IEventLog   │  │IToolRuntime │  │IPolicyEngine│        ┃ ║
║  ┃  │ 执行引擎    │  │ 事件日志    │  │ 工具门禁    │  │ 策略引擎    │        ┃ ║
║  ┃  │             │  │             │  │             │  │             │        ┃ ║
║  ┃  │ ·run()      │  │ ·append()   │  │ ·invoke()   │  │ ·check()    │        ┃ ║
║  ┃  │ ·resume()   │  │ ·query()    │  │ ·register() │  │ ·enforce()  │        ┃ ║
║  ┃  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          ┃ ║
║  ┃  │TrustBoundary│  │IContextAssem│  │ IValidator  │                          ┃ ║
║  ┃  │ 信任边界    │  │ 上下文装配  │  │ 验证器      │                          ┃ ║
║  ┃  └─────────────┘  └─────────────┘  └─────────────┘                          ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                         │                                         ║
║                                         ▼                                         ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ Layer 2: Pluggable Components（可插拔，框架提供默认实现）                    ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  ┌─────────────────────────────────────────────────────────────────────┐    ┃ ║
║  ┃  │ IModelAdapter                     IMemory                            │    ┃ ║
║  ┃  │ ├── ClaudeAdapter ✅              ├── InMemoryMemory ✅              │    ┃ ║
║  ┃  │ ├── OpenAIAdapter ✅              ├── VectorMemory ✅                │    ┃ ║
║  ┃  │ └── OllamaAdapter ✅              └── FileMemory ✅                  │    ┃ ║
║  ┃  └─────────────────────────────────────────────────────────────────────┘    ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  ┌─────────────────────────────────────────────────────────────────────┐    ┃ ║
║  ┃  │ ITool / IToolkit                  IMCPClient                         │    ┃ ║
║  ┃  │ ├── ReadFileTool ✅               ├── StdioMCPClient ✅              │    ┃ ║
║  ┃  │ ├── WriteFileTool ✅              └── SSEMCPClient ✅                │    ┃ ║
║  ┃  │ ├── SearchCodeTool ✅                                                │    ┃ ║
║  ┃  │ ├── RunCommandTool ✅             MCPToolkit ✅ (MCP→ITool 桥接)     │    ┃ ║
║  ┃  │ └── RunTestsTool ✅                                                  │    ┃ ║
║  ┃  └─────────────────────────────────────────────────────────────────────┘    ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  ┌─────────────────────────────────────────────────────────────────────┐    ┃ ║
║  ┃  │ ISkill                            IHook                              │    ┃ ║
║  ┃  │ └── (开发者定义业务技能)          ├── LoggingHook ✅                 │    ┃ ║
║  ┃  │                                   └── MetricsHook ✅                 │    ┃ ║
║  ┃  └─────────────────────────────────────────────────────────────────────┘    ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  ┌─────────────────────────────────────────────────────────────────────┐    ┃ ║
║  ┃  │ 新增（学习自 Pydantic AI）                                           │    ┃ ║
║  ┃  │ ├── RunContext[DepsT]         泛型依赖注入上下文                     │    ┃ ║
║  ┃  │ ├── IStreamedResponse[T]      流式响应接口                           │    ┃ ║
║  ┃  │ └── ICheckpoint               状态持久化（增强自 AgentScope）         │    ┃ ║
║  ┃  └─────────────────────────────────────────────────────────────────────┘    ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                         │                                         ║
║                                         ▼                                         ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ Layer 3: Agent Composition（开发者组装）                                     ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  AgentBuilder[DepsT, OutputT]                                                ┃ ║
║  ┃  ├── .with_model(IModelAdapter)                                              ┃ ║
║  ┃  ├── .with_tools(ITool...)                                                   ┃ ║
║  ┃  ├── .with_mcp(IMCPClient...)                                                ┃ ║
║  ┃  ├── .with_memory(IMemory)                                                   ┃ ║
║  ┃  ├── .with_skills(ISkill...)                                                 ┃ ║
║  ┃  ├── .with_hooks(IHook...)                                                   ┃ ║
║  ┃  └── .build() → Agent[DepsT, OutputT]                                        ┃ ║
║  ┃                                                                              ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
```

---

## 二、接口完整清单

### 2.1 Layer 1: Core Infrastructure（7 个接口）

| 接口 | 职责 | 关键方法 | 默认实现 |
|-----|------|---------|---------|
| `IRuntime` | 执行引擎，编排三层循环 | `run()`, `resume()`, `cancel()` | `AgentRuntime` |
| `IEventLog` | 事件日志，append-only | `append()`, `query()`, `verify_chain()` | `LocalEventLog` |
| `IToolRuntime` | 工具执行门禁 | `invoke()`, `register()`, `list_tools()` | `ToolRuntime` |
| `IPolicyEngine` | 策略检查与执行 | `check()`, `enforce()`, `register_policy()` | `PolicyEngine` |
| `TrustBoundary` | 信任边界验证 | `validate_step()`, `derive_safe_fields()` | 框架内置 |
| `IContextAssembler` | 上下文装配 | `assemble()`, `compress()` | `ContextAssembler` |
| `IValidator` | 验证器 | `validate()` | 多个内置验证器 |

### 2.2 Layer 2: Pluggable Components（8 个接口）

| 接口 | 职责 | 内置实现 | 可扩展 |
|-----|------|---------|--------|
| `IModelAdapter` | LLM 适配 | `ClaudeAdapter`, `OpenAIAdapter`, `OllamaAdapter` | ✅ |
| `IMemory` | 记忆管理 | `InMemoryMemory`, `VectorMemory`, `FileMemory` | ✅ |
| `ITool` | 单个工具 | `ReadFileTool`, `WriteFileTool`, `SearchCodeTool`, `RunCommandTool`, `RunTestsTool` | ✅ |
| `IToolkit` | 工具集 | `MCPToolkit` | ✅ |
| `IMCPClient` | MCP 客户端 | `StdioMCPClient`, `SSEMCPClient` | ✅ |
| `ISkill` | 复合技能 | （开发者定义） | ✅ |
| `IHook` | 生命周期钩子 | `LoggingHook`, `MetricsHook` | ✅ |
| `ICheckpoint` | 状态持久化 | `FileCheckpoint` | ✅ |

### 2.3 新增接口（学习自 Pydantic AI）

| 接口 | 来源 | 职责 |
|-----|------|------|
| `RunContext[DepsT]` | Pydantic AI | 泛型依赖注入上下文 |
| `IStreamedResponse[T]` | Pydantic AI | 流式响应抽象 |

### 2.4 数据结构（循环模型需要）

| 数据结构 | 职责 | 所属循环 |
|---------|------|---------|
| `Task` | 任务定义 | Session Loop |
| `Milestone` | 里程碑定义 | Milestone Loop |
| `ValidatedStep` | 验证后的步骤 | Milestone Loop |
| `Envelope` | WorkUnit 执行边界 | Tool Loop |
| `DonePredicate` | 完成条件 | Tool Loop |
| `Budget` | 预算限制 | Tool Loop |

---

## 三、接口如何构成三层循环

### 3.1 循环与接口的映射关系

```
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                              三层循环接口映射                                       ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                    ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ SESSION LOOP（跨 Context Window）                                            ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  使用的接口：                                                                ┃ ║
║  ┃  ├── IRuntime.run()           启动执行                                       ┃ ║
║  ┃  ├── IRuntime.resume()        断点续跑                                       ┃ ║
║  ┃  ├── ICheckpoint.save/load()  状态持久化                                     ┃ ║
║  ┃  ├── IEventLog.append()       记录 session 事件                              ┃ ║
║  ┃  └── IMemory.store/search()   跨 session 记忆                                ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  产物：TaskPlan, ProgressLog, EventLog, Git Commit                          ┃ ║
║  ┃                                                                              ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                         │                                         ║
║                              每个 Milestone ↓                                      ║
║                                                                                    ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ MILESTONE LOOP（Observe → Plan → Validate → Execute → Verify）               ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐       ┃ ║
║  ┃  │ Observe │──▶│  Plan   │──▶│ Validate │──▶│ Execute │──▶│ Verify  │       ┃ ║
║  ┃  └────┬────┘   └────┬────┘   └────┬─────┘   └────┬────┘   └────┬────┘       ┃ ║
║  ┃       │             │             │              │             │             ┃ ║
║  ┃       ▼             ▼             ▼              ▼             ▼             ┃ ║
║  ┃  IContext     IModel        TrustBoundary  IToolRuntime  IValidator          ┃ ║
║  ┃  Assembler    Adapter       IPolicy        (Atomic)      DonePredicate       ┃ ║
║  ┃  IMemory      .generate()   Engine         或 ToolLoop                       ┃ ║
║  ┃                                            (WorkUnit)                        ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  产物：ValidatedSteps, Evidence, VerifyReport                                ┃ ║
║  ┃                                                                              ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                         │                                         ║
║                        只有 WorkUnit Step ↓ 进入                                   ║
║                                                                                    ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ TOOL LOOP（Gather → Act → Check → Update）                                   ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  边界：Envelope（allowed_tools, budget, required_evidence）                  ┃ ║
║  ┃  结束：DonePredicate 满足 OR Budget 耗尽 OR 停滞检测                         ┃ ║
║  ┃                                                                              ┃ ║
║  ┃      ┌────────┐   ┌───────┐   ┌───────┐   ┌────────┐                        ┃ ║
║  ┃      │ Gather │──▶│  Act  │──▶│ Check │──▶│ Update │──┐                     ┃ ║
║  ┃      └────┬───┘   └───┬───┘   └───┬───┘   └────┬───┘  │                     ┃ ║
║  ┃           │           │           │            │       │                     ┃ ║
║  ┃           ▼           ▼           ▼            ▼       │                     ┃ ║
║  ┃      IContext    IModel      IToolRuntime  IEventLog   │                     ┃ ║
║  ┃      Assembler   Adapter     ·invoke()     ·append()   │                     ┃ ║
║  ┃      IMemory     (工具选择)   (门禁检查)    (证据收集)  │                     ┃ ║
║  ┃           ▲                                            │                     ┃ ║
║  ┃           └────────────────────────────────────────────┘                     ┃ ║
║  ┃                                                                              ┃ ║
║  ┃  产物：ToolResults, 局部证据                                                 ┃ ║
║  ┃                                                                              ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
```

### 3.2 各阶段使用的接口详解

| 循环 | 阶段 | 使用的接口 | 作用 |
|-----|------|-----------|------|
| **Session** | 初始化 | `IRuntime.run()` | 启动任务执行 |
| | 恢复 | `ICheckpoint.load()`, `IRuntime.resume()` | 从断点恢复 |
| | 持久化 | `ICheckpoint.save()`, `IEventLog.append()` | 保存状态和日志 |
| **Milestone** | Observe | `IContextAssembler.assemble()`, `IMemory.search()` | 收集上下文 |
| | Plan | `IModelAdapter.generate()` | LLM 规划步骤 |
| | Validate | `TrustBoundary`, `IPolicyEngine.check()` | 验证步骤安全性 |
| | Execute | `IToolRuntime.invoke()` 或进入 Tool Loop | 执行步骤 |
| | Verify | `IValidator.validate()`, `DonePredicate` | 验收结果 |
| **Tool Loop** | Gather | `IContextAssembler`, `IMemory` | 收集当前状态 |
| | Act | `IModelAdapter.generate()` | 选择下一个工具 |
| | Check | `IToolRuntime.invoke()` (内含门禁) | 检查并执行工具 |
| | Update | `IEventLog.append()` | 记录证据 |

---

## 四、内置实现完整列表

### 4.1 模型适配器 (IModelAdapter)

| 实现 | 状态 | 支持模型 | 说明 |
|-----|------|---------|------|
| `ClaudeAdapter` | ✅ 内置 | claude-sonnet-4, claude-opus-4-5 | Anthropic API |
| `OpenAIAdapter` | ✅ 内置 | gpt-4o, gpt-4o-mini | OpenAI API |
| `OllamaAdapter` | ✅ 内置 | llama, mistral, etc. | 本地模型 |
| `AzureOpenAIAdapter` | 🔜 可选 | Azure 部署的 GPT | Azure 托管 |
| `BedrockAdapter` | 🔜 可选 | AWS 托管模型 | AWS Bedrock |

### 4.2 记忆实现 (IMemory)

| 实现 | 状态 | 适用场景 | 特点 |
|-----|------|---------|------|
| `InMemoryMemory` | ✅ 内置 | 开发/测试 | 无持久化，快速 |
| `VectorMemory` | ✅ 内置 | 语义搜索 | 支持嵌入向量 |
| `FileMemory` | ✅ 内置 | 简单持久化 | JSON 文件存储 |
| `PostgresMemory` | 🔜 可选 | 生产环境 | 关系数据库 |
| `RedisMemory` | 🔜 可选 | 分布式场景 | 高性能缓存 |

### 4.3 工具实现 (ITool)

| 实现 | 状态 | 风险级别 | 说明 |
|-----|------|---------|------|
| `ReadFileTool` | ✅ 内置 | READ_ONLY | 读取文件内容 |
| `WriteFileTool` | ✅ 内置 | IDEMPOTENT_WRITE | 写入文件 |
| `SearchCodeTool` | ✅ 内置 | READ_ONLY | 代码搜索（grep/ripgrep） |
| `RunCommandTool` | ✅ 内置 | NON_IDEMPOTENT | 执行 shell 命令 |
| `RunTestsTool` | ✅ 内置 | READ_ONLY | 运行测试套件 |
| `ListDirectoryTool` | ✅ 内置 | READ_ONLY | 列出目录内容 |

### 4.4 MCP 客户端 (IMCPClient)

| 实现 | 状态 | 传输方式 | 说明 |
|-----|------|---------|------|
| `StdioMCPClient` | ✅ 内置 | stdio | 本地进程通信 |
| `SSEMCPClient` | ✅ 内置 | HTTP SSE | 远程服务器 |
| `WebSocketMCPClient` | 🔜 可选 | WebSocket | 双向实时通信 |

### 4.5 钩子实现 (IHook)

| 实现 | 状态 | 作用 |
|-----|------|------|
| `LoggingHook` | ✅ 内置 | 记录执行日志 |
| `MetricsHook` | ✅ 内置 | 收集性能指标 |
| `TracingHook` | 🔜 可选 | OpenTelemetry 集成 |

### 4.6 核心基础设施默认实现

| 接口 | 默认实现 | 说明 |
|-----|---------|------|
| `IRuntime` | `AgentRuntime` | 三层循环编排 |
| `IEventLog` | `LocalEventLog` | 本地 append-only 日志 |
| `IToolRuntime` | `ToolRuntime` | 工具门禁 |
| `IPolicyEngine` | `PolicyEngine` | 策略检查 |
| `IContextAssembler` | `ContextAssembler` | 上下文装配 |
| `ICheckpoint` | `FileCheckpoint` | 文件系统持久化 |

---

## 五、循环实现伪代码

### 5.1 IRuntime 实现（编排三层循环）

```python
class AgentRuntime(IRuntime, Generic[DepsT, OutputT]):
    """
    执行引擎：编排三层循环
    """

    def __init__(
        self,
        event_log: IEventLog,
        tool_runtime: IToolRuntime,
        policy_engine: IPolicyEngine,
        context_assembler: IContextAssembler,
        model_adapter: IModelAdapter,
        checkpoint: ICheckpoint,
    ):
        self.event_log = event_log
        self.tool_runtime = tool_runtime
        self.policy_engine = policy_engine
        self.context_assembler = context_assembler
        self.model_adapter = model_adapter
        self.checkpoint = checkpoint

    async def run(
        self,
        task: Task,
        deps: DepsT,
    ) -> RunResult[OutputT]:
        """
        执行任务（Session Loop 入口）
        """
        ctx = RunContext(
            deps=deps,
            run_id=generate_id(),
            session_id=generate_id(),
        )

        # Session Loop
        return await self._session_loop(task, ctx)

    async def _session_loop(
        self,
        task: Task,
        ctx: RunContext[DepsT],
    ) -> RunResult[OutputT]:
        """Session Loop：跨 context window"""

        # 尝试恢复
        state = await self.checkpoint.load(task.task_id)
        if state:
            milestones = state.remaining_milestones
        else:
            milestones = await self._plan_milestones(task, ctx)

        await self.event_log.append(SessionStartEvent(ctx.session_id))

        for milestone in milestones:
            # Milestone Loop
            result = await self._milestone_loop(milestone, ctx)

            # 保存 checkpoint
            await self.checkpoint.save(CheckpointState(
                task_id=task.task_id,
                remaining_milestones=milestones[milestones.index(milestone)+1:],
            ))

            if not result.success and milestone.is_critical:
                return RunResult(success=False, error=result.error)

        return RunResult(success=True, output=self._build_output(ctx))

    async def _milestone_loop(
        self,
        milestone: Milestone,
        ctx: RunContext[DepsT],
    ) -> MilestoneResult:
        """Milestone Loop：Plan → Validate → Execute → Verify"""

        # === Observe ===
        context = await self.context_assembler.assemble(milestone, ctx)

        # === Plan (LLM, 不可信) ===
        proposed = await self.model_adapter.generate(
            messages=self._build_plan_prompt(context),
            tools=self.tool_runtime.list_tools(),
        )
        proposed_steps = self._parse_steps(proposed)

        # === Validate (系统, 可信) ===
        validated_steps = await self._validate_steps(proposed_steps, ctx)

        # === Execute ===
        for step in validated_steps:
            if step.step_type == StepType.ATOMIC:
                # 直接调用工具
                result = await self.tool_runtime.invoke(
                    step.tool_name,
                    step.tool_input,
                    ctx,
                )
            else:  # WORK_UNIT
                # 进入 Tool Loop
                result = await self._tool_loop(step, ctx)

            await self.event_log.append(StepExecutedEvent(step, result))

        # === Verify ===
        return await self._verify(milestone, validated_steps, ctx)

    async def _tool_loop(
        self,
        step: ValidatedStep,
        ctx: RunContext[DepsT],
    ) -> ToolLoopResult:
        """Tool Loop：Gather → Act → Check → Update"""

        envelope = step.envelope
        done_pred = step.done_predicate
        evidence = []
        budget = BudgetTracker(envelope.budget)

        while not done_pred.is_satisfied(evidence):
            # 检查终止条件
            if budget.is_exceeded():
                return ToolLoopResult(success=False, error="budget_exceeded")

            # === Gather ===
            gather_ctx = await self.context_assembler.assemble_for_tool_loop(
                step, evidence, ctx
            )

            # === Act ===
            action = await self.model_adapter.generate(
                messages=self._build_action_prompt(gather_ctx),
                tools=[t for t in self.tool_runtime.list_tools()
                       if t.name in envelope.allowed_tools],
            )

            if not action.tool_calls:
                break

            tool_call = action.tool_calls[0]

            # === Check (门禁) ===
            if tool_call.name not in envelope.allowed_tools:
                await self.event_log.append(ToolDeniedEvent(tool_call, "not_allowed"))
                continue

            result = await self.tool_runtime.invoke(
                tool_call.name,
                tool_call.arguments,
                ctx,
                envelope=envelope,  # 传入边界信息
            )

            budget.record_call()

            # === Update ===
            if result.evidence_ref:
                evidence.append(result.evidence_ref)

            await self.event_log.append(ToolExecutedEvent(tool_call, result))

        return ToolLoopResult(
            success=done_pred.is_satisfied(evidence),
            evidence=evidence,
        )

    async def _validate_steps(
        self,
        proposed: list[ProposedStep],
        ctx: RunContext,
    ) -> list[ValidatedStep]:
        """
        Validate 阶段：信任边界

        关键：LLM 提出的步骤经过 4 道 Gate 验证
        """
        validated = []

        for step in proposed:
            # Gate 1: 工具/技能存在性检查
            if not self._tool_or_skill_exists(step):
                continue

            # Gate 2: 策略检查
            policy_result = await self.policy_engine.check(
                action="invoke_tool" if step.is_atomic else "invoke_skill",
                resource=step.name,
                context=ctx,
            )
            if not policy_result.allowed:
                continue

            # Gate 3: 从 Registry 派生安全字段（不信任 LLM）
            safe_step = self._derive_safe_fields(step)

            # Gate 4: 生成 Envelope（WorkUnit 专用）
            if step.step_type == StepType.WORK_UNIT:
                safe_step.envelope = self._generate_envelope(step)
                safe_step.done_predicate = self._get_done_predicate(step)

            validated.append(safe_step)

        return validated
```

---

## 六、学习融合总结

### 6.1 从 Pydantic AI 学习的设计

| 设计 | 采纳状态 | 影响 |
|-----|---------|------|
| `RunContext[DepsT]` 泛型上下文 | ✅ 采纳 | 类型安全的依赖注入 |
| `Agent[DepsT, OutputT]` 泛型 Agent | ✅ 采纳 | 结构化输出类型检查 |
| `IStreamedResponse[T]` | ✅ 采纳 | 流式响应支持 |
| Toolset `filter()`, `prefix()` | ✅ 采纳 | 工具集灵活管理 |

### 6.2 从 AgentScope 学习的设计

| 设计 | 采纳状态 | 影响 |
|-----|---------|------|
| `StateModule` 嵌套状态 | ✅ 采纳 | `ICheckpoint` 增强 |
| Toolkit 分组管理 | ✅ 采纳 | `IToolkit.activate_group()` |
| `FormatterBase` | 🔜 后续 | Prompt 格式化 |

### 6.3 DARE 独有设计（保持差异化）

| 设计 | 说明 | 其他框架没有 |
|-----|------|------------|
| `TrustBoundary` | LLM 输出不可信，安全字段从 Registry 派生 | ✅ |
| `IEventLog` + Hash Chain | Append-only 审计日志，防篡改 | ✅ |
| `ToolRiskLevel` | 工具风险分级（READ_ONLY → COMPENSATABLE） | ✅ |
| `IPolicyEngine` | 策略即代码，权限控制 | ✅ |
| `Envelope` + `DonePredicate` | WorkUnit 执行边界和完成条件 | ✅ |
| 五个可验证闭环 | 每个安全机制都可证明 | ✅ |

---

## 七、使用示例

### 7.1 开箱即用（零配置）

```python
from dare_framework import AgentBuilder

agent = AgentBuilder.quick_start(
    name="my-agent",
    model="claude-sonnet",
)

result = await agent.run(Task(description="读取 README.md 并总结"))
```

### 7.2 混合使用（选择性配置）

```python
from dare_framework import AgentBuilder
from dare_framework.models import ClaudeAdapter
from dare_framework.tools import ReadFileTool, WriteFileTool
from dare_framework.memory import VectorMemory

agent = (
    AgentBuilder("coding-agent")
    .with_model(ClaudeAdapter())
    .with_tools(ReadFileTool(), WriteFileTool())
    .with_memory(VectorMemory())
    .build()
)
```

### 7.3 完全自定义（高级用户）

```python
from dataclasses import dataclass
from dare_framework import AgentBuilder, RunContext

@dataclass
class MyDeps:
    workspace: Path
    db: Database

class MyOutput(BaseModel):
    files_modified: list[str]
    tests_passed: bool

agent: Agent[MyDeps, MyOutput] = (
    AgentBuilder("my-agent")
    .with_model(MyCustomAdapter())
    .with_tools(MyTool1(), MyTool2())
    .with_memory(MyMemory())
    .with_hooks(MyHook())
    .with_output_type(MyOutput)
    .build()
)

result = await agent.run(
    task=Task(description="..."),
    deps=MyDeps(workspace=Path("."), db=db),
)
# result.output: MyOutput（有类型！）
```

---

*文档状态：架构终稿评审 v1*
