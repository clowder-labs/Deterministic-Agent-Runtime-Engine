# DARE Framework 详细 PPT 素材 — 基于源码

> **重要**：本文档仅基于 `dare_framework/` 和 `examples/05-dare-coding-agent-enhanced/` 的**源码**分析而成，不引用 doc/、openspec/ 等外部文档。供 Notebook LM 生成详细 PPT 与流程图使用。
>
> **文档要求**：每个组件必须包含 **① 工作逻辑图**（流程图/时序图）和 **② 要点说明**（输入/输出、关键步骤、与上下游衔接、可扩展点）。

---

# P1：框架整体架构图

## 1.1 组件层次结构（从源码归纳）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 3: 开发者 API / Builder 层                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │ DareAgentBuilder | ReactAgentBuilder | SimpleChatAgentBuilder             │  │
│  │ 链式配置：with_model / with_prompt(store/id) / add_tools / with_knowledge  │  │
│  │          / with_long_term_memory / with_embedding_adapter / with_skill     │  │
│  │          / with_planner / add_validators / with_remediator / with_event_log│  │
│  │          / with_execution_control / with_telemetry / with_config / ...     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 2: 编排层（Agent 实现）                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────────────┐    │
│  │   DareAgent     │  │   ReactAgent    │  │      SimpleChatAgent          │    │
│  │ 五层编排+会话   │  │ ReAct 工具循环  │  │ 单次对话/无工具循环           │    │
│  └─────────────────┘  └─────────────────┘  └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 1: 核心域组件（可插拔）                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Context  │ │  Model   │ │   Plan   │ │   Tool   │ │Knowledge │ │  Memory  │  │
│  │ 上下文   │ │ 模型适配 │ │ 计划校验 │ │ 工具调用 │ │ 知识库   │ │ STM/LTM  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Event   │ │   Hook   │ │ Observability│ │  Config  │ │  Skill   │           │
│  │ 事件日志 │ │ 扩展点   │ │ 观测/遥测    │ │ 配置     │ │ 技能    │           │
│  └──────────┘ └──────────┘ └──────────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                                         │
│  │ Security │ │ Embedding│ │   A2A    │                                         │
│  │ 风险策略 │ │ 向量适配 │ │ 协议适配 │                                         │
│  └──────────┘ └──────────┘ └──────────┘                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 0: 边界与基础设施                                                          │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │ IToolGateway/Manager│  │ IEventLog           │  │ IExecutionControl   │      │
│  │ 工具调用边界/注册表 │  │ 审计/可重放         │  │ HITL 控制           │      │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘      │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │ ITelemetryProvider  │  │ IConfigProvider     │  │ ISessionSummaryStore│      │
│  │ 遥测/Tracing        │  │ 配置快照            │  │ 会话摘要持久化      │      │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 1.2 各层组件清单与扩展方向（源码依据）

| 层级 | 组件 | 源码路径 | 扩展方式 |
|------|------|----------|----------|
| **L3 Builder** | DareAgentBuilder | agent/_internal/builder.py | 继承 _BaseAgentBuilder，实现 _build_impl() |
| **L3 Builder** | ReactAgentBuilder | agent/_internal/builder.py | 同上 |
| **L3 Builder** | SimpleChatAgentBuilder | agent/_internal/builder.py | 同上 |
| **L2 编排** | DareAgent | agent/_internal/five_layer.py | 实现 IAgentOrchestration 或自定义执行模式 |
| **L2 编排** | ReactAgent | agent/_internal/react_agent.py | 覆写 _execute() 或自定义 ReAct 循环 |
| **L2 编排** | SimpleChatAgent | agent/_internal/simple_chat.py | 纯对话模式，覆写 _execute() |
| **L1 Context** | Context | context/_internal/context.py | 实现 IContext，覆写 assemble()/compress() |
| **L1 Model** | OpenRouterModelAdapter | model/_internal/openrouter_adapter.py | 实现 IModelAdapter.generate() |
| **L1 Model** | OpenAIModelAdapter | model/_internal/openai_adapter.py | LangChain 适配，支持自定义 endpoint |
| **L1 Model** | DefaultModelAdapterManager | model/_internal/default_model_adapter_manager.py | 基于 Config.llm 解析模型 |
| **L1 Prompt** | LayeredPromptStore | model/_internal/layered_prompt_store.py | 叠加 FileSystem + Builtin Prompt |
| **L1 Plan** | DefaultPlanner | plan/_internal/default_planner.py | 实现 IPlanner.plan()/decompose() |
| **L1 Plan** | CompositeValidator | plan/_internal/composite_validator.py | 组合多个 IValidator |
| **L1 Plan** | DefaultRemediator | plan/_internal/default_remediator.py | 实现 IRemediator.remediate() |
| **L1 Plan** | DefaultPlanAttemptSandbox | agent/_internal/sandbox.py | IPlanAttemptSandbox：STM 快照/回滚 |
| **L1 Tool** | ToolManager | tool/_internal/managers/tool_manager.py | 实现 IToolManager/IToolGateway |
| **L1 Tool** | Native Tools | tool/_internal/tools/*.py | 实现 ITool（name, input_schema, execute 等） |
| **L1 Tool** | MCPToolkit | tool/_internal/toolkits/mcp_toolkit.py | MCP 工具适配（stdio/http） |
| **L1 Tool** | SearchSkillTool / SkillScriptRunner | skill/_internal/*.py | auto_skill_mode 的工具入口 |
| **L1 Knowledge** | RawDataKnowledge | knowledge/_internal/rawdata_knowledge/ | 实现 IKnowledge.get/add |
| **L1 Knowledge** | VectorKnowledge | knowledge/_internal/vector_knowledge/ | 同上（需 embedding adapter） |
| **L1 Memory** | InMemorySTM | memory/_internal/in_memory_stm.py | 实现 IShortTermMemory |
| **L1 Memory** | RawDataLongTermMemory | memory/_internal/rawdata_ltm.py | ILongTermMemory（substring 检索） |
| **L1 Memory** | VectorLongTermMemory | memory/_internal/vector_ltm.py | ILongTermMemory（向量检索） |
| **L1 Hook** | HookExtensionPoint | hook/_internal/hook_extension_point.py | HookPhase 生命周期扩展 |
| **L1 Observability** | ObservabilityHook | observability/_internal/tracing_hook.py | Hook→Tracing/Metrics |
| **L1 Event** | IEventLog | event/kernel.py | append/query/replay/verify_chain |
| **L1 Event** | TraceAwareEventLog | observability/_internal/event_trace_bridge.py | 事件写入自动附带 trace_id |
| **L1 Config** | Config | config/types.py | 扩展字段（llm/observability/skill_mode 等） |
| **L1 Config** | FileConfigProvider | config/_internal/file_config_provider.py | 分层读取 .dare/config.json |
| **L1 Security** | RiskLevel/PolicyDecision | security/types.py | 风险级别/审批策略 |
| **L1 Embedding** | IEmbeddingAdapter | embedding/interfaces.py | 向量知识库与 LTM 依赖 |
| **L1 A2A** | A2A Server/Client | a2a/server/*, a2a/client/* | JSON-RPC + AgentCard 适配 |

## 1.3 数据流总览（可用于画图）

```
User Task (str | Task)
        │
        ▼
   IAgent.run()
        │
        ├─► [Full Five-Layer] Session → Milestone → Plan → Execute → Tool → Verify → SessionSummary
        ├─► [ReAct] Execute → Tool (无 Plan/Verify)
        └─► [Simple] 单次 model.generate()
        │
        ▼
   RunResult(success, output, errors, session_id, session_summary?)
```

---

# P2：框架支持的外部挂载与集成

## 2.1 MCP（Model Context Protocol）

**挂载方式**：
- Config.mcp_paths 指定配置目录（如 `.dare/mcp/`），路径会按 workspace_dir 解析
- Builder.build() 时自动调用 load_mcp_toolkit() → 解析配置并初始化 MCPToolkit

**支持 transport**：
- `stdio`、`http` 已实现；`grpc` 在配置类型中存在，但工厂会抛错（未实现）

**配置示例**（mcp/types.py）：
```json
{
  "name": "local_math",
  "transport": "http",
  "url": "http://127.0.0.1:8765/",
  "timeout_seconds": 30
}
```

**流程**：load_mcp_configs → create_mcp_clients(connect=True) → MCPToolkit.initialize() → list_tools() 返回 MCPTool 列表，工具名格式 `server:tool`（如 `local_math:add`）

**过滤**：Config.allowmcps 可限制启用的 MCP 服务器列表。

**工作逻辑图**：

```
Builder.build()
    └─► load_mcp_toolkit(config)
            ├─► load_mcp_configs(paths, workspace_dir, user_dir)
            ├─► create_mcp_clients(connect=True, skip_errors=True)
            └─► MCPToolkit.initialize() → list_tools() → MCPTool(full_name)
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | Config.mcp_paths / allowmcps；支持 JSON/YAML/MD（代码块）配置。 |
| **输出** | MCPToolkit (IToolProvider)，list_tools() 返回 MCPTool 列表。 |
| **关键步骤** | 路径解析（workspace_dir 相对路径）→ 解析配置 → 创建客户端 → connect → list_tools → 生成 full_name。 |
| **与上下游** | 上游：Builder.build()；下游：_resolved_tools 合并 MCP 工具 → ToolManager 注册。 |
| **可扩展点** | 新 transport（grpc/自定义）；实现 IMCPClient。 |

## 2.2 Skill（Agent Skills 格式，含两种模式）

### 2.2.1 Persistent Skill Mode（默认）

**挂载方式**：
- Builder.with_skill(path) 或 Config.initial_skill_path

**注入时机**：
- Builder.build() → _load_initial_skill_and_mount() → context.set_skill()
- 构建时将 skill 内容合并进 sys_prompt（enrich_prompt_with_skill）

**工作逻辑图**：

```
build()
  └─► load skill (FileSystemSkillLoader)
       └─► context.set_skill(skill)
           └─► sys_prompt = enrich_prompt_with_skill(sys_prompt, skill)
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | initial_skill_path 或 with_skill(path)。 |
| **输出** | Context.current_skill() 指向单一 Skill；sys_prompt 已包含完整 skill 内容。 |
| **关键步骤** | 只取 loader.load() 的第一个 skill，合并进 prompt。 |
| **与上下游** | 上游：Builder；下游：Context.assemble() 直接使用已合并 sys_prompt。 |
| **可扩展点** | 自定义 ISkillLoader；自定义 prompt_enricher。 |

### 2.2.2 Auto Skill Mode（目录扫描 + 工具加载）

**开启方式**：
- Config.skill_mode = "auto_skill_mode"
- Config.skill_paths 提供技能目录（支持 workspace 相对路径）

**运行机制**：
- Builder 在 build 时加载 SkillStore；sys_prompt 仅追加“技能目录摘要”
- 自动注入工具：`search_skill`（加载完整 skill 内容到 Context）+ `run_skill_script`
- Context.assemble() 会把已加载 skill 的完整内容合并到下一次模型输入

**工作逻辑图**：

```
build()
  ├─► SkillStore(loader).reload() → skills
  ├─► sys_prompt = enrich_prompt_with_skill_summaries(sys_prompt, skills)
  ├─► tools += SearchSkillTool + SkillScriptRunner
  └─► Agent运行时:
        ├─► search_skill(skill_id) → context.add_loaded_full_skill(skill)
        └─► assemble() → sys_prompt + full skill content
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | skill_mode=auto_skill_mode + skill_paths。 |
| **输出** | sys_prompt 中仅有 skill 摘要，完整内容需通过 search_skill 加载。 |
| **关键步骤** | SearchSkillTool 将 Skill 存入 Context；assemble() 合并进 sys_prompt。 |
| **与上下游** | 上游：Config/Builder；下游：模型在工具调用后获得完整技能指引。 |
| **可扩展点** | 自定义 ISkillSelector（如关键字筛选）；扩展 SkillScriptRunner。 |

## 2.3 Knowledge 库

**挂载方式**：
- Builder.with_knowledge(knowledge) 显式注入
- 或 Config.knowledge + with_embedding_adapter（vector 类型）

**类型**：
- **rawdata**：RawDataKnowledge，substring 检索；storage 可选 in_memory | sqlite
- **vector**：VectorKnowledge，需 IEmbeddingAdapter；storage 可选 in_memory | sqlite | chromadb

**工具暴露**：框架自动注册 knowledge_get、knowledge_add 到 ToolManager。

**工作逻辑图**：

```
Builder._register_tools_with_manager()
    └─► if knowledge: register KnowledgeGetTool / KnowledgeAddTool
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | knowledge 实例或 Config.knowledge（type/storage/options）。 |
| **输出** | knowledge_get / knowledge_add 工具可被模型调用。 |
| **关键步骤** | create_knowledge 根据配置创建 RawDataKnowledge/VectorKnowledge。 |
| **与上下游** | 上游：Builder；下游：ToolManager 注册为工具；Agent 直接调用。 |
| **可扩展点** | 新增 IKnowledge 或自定义存储/向量库。 |

## 2.4 Long-Term Memory（LTM）

**挂载方式**：
- Builder.with_long_term_memory(ltm) 显式注入
- 或 Config.long_term_memory + with_embedding_adapter（vector 类型）

**类型**：
- **RawDataLongTermMemory**：substring 检索
- **VectorLongTermMemory**：向量检索（需 embedding adapter）

**工作逻辑图**：

```
create_long_term_memory(config, embedding_adapter)
    ├─► rawdata → RawDataLongTermMemory(storage)
    └─► vector  → VectorLongTermMemory(embedding_adapter, vector_store)
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | Config.long_term_memory 或 with_long_term_memory。 |
| **输出** | ILongTermMemory（get/query + persist）。 |
| **关键步骤** | rawdata 用 RawDataStore；vector 用 VectorStore + embedding。 |
| **与上下游** | 上游：Builder；下游：Context.long_term_memory 持有，但 assemble 默认不自动检索。 |
| **可扩展点** | 自定义 ILongTermMemory 或持久化策略。 |

## 2.5 本地 Tools

**挂载方式**：Builder.add_tools(*tools)

**内置工具**（tool/_internal/tools）：ReadFileTool、WriteFileTool、SearchCodeTool、RunCommandTool、EditLineTool、EchoTool、NoopTool 等。

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | ITool 实例，提供 name/description/schema/execute。 |
| **输出** | ToolManager 注册能力描述符，供模型 list_tool_defs。 |
| **关键步骤** | ToolManager 将工具转换为 CapabilityDescriptor 并生成 tool_defs。 |
| **与上下游** | 上游：Builder；下游：ModelInput.tools。 |
| **可扩展点** | 定义新工具，设定 risk_level / requires_approval / capability_kind。 |

## 2.6 Hook 与 Observability

**挂载方式**：
- DareAgentBuilder.add_hooks(*hooks)
- 或 with_managers(hook_manager=...) 从配置加载
- telemetry 为 OTelTelemetryProvider 时，DareAgent 自动注入 ObservabilityHook

**工作逻辑图**：

```
DareAgent._emit_hook(phase, payload)
    └─► HookExtensionPoint.emit()
          ├─► callbacks(同步)
          └─► IHook.invoke(异步)
                └─► ObservabilityHook → Telemetry(Tracing/Metrics)
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | HookPhase + payload（run_id, task_id, budget_stats 等）。 |
| **输出** | 无强制返回值；ObservabilityHook 记录 span/metric。 |
| **关键步骤** | HookExtensionPoint 先回调 callbacks，再调用 hooks；异常仅日志。 |
| **与上下游** | 上游：Agent 生命周期；下游：Telemetry Provider（OTel）。 |
| **可扩展点** | 新 Hook（审批/日志/指标/审计）。 |

## 2.7 模型（Model）

**挂载方式**：
- Builder.with_model(model)
- 或 IModelAdapterManager（默认使用 Config.llm 解析）

**内置实现**：
- OpenRouterModelAdapter（OpenAI Async SDK）
- OpenAIModelAdapter（LangChain ChatOpenAI）

**工作逻辑图**：

```
Builder._resolved_model()
    ├─► explicit model
    └─► DefaultModelAdapterManager.load_model_adapter(Config.llm)

运行时: Context.assemble() → ModelInput(messages, tools) → model.generate()
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | ModelInput(messages, tools, metadata) + GenerateOptions。 |
| **输出** | ModelResponse(content, tool_calls, usage, metadata)。 |
| **关键步骤** | OpenRouter 直接用 OpenAI SDK；OpenAIModelAdapter 绑定 tool_defs（LangChain）。 |
| **与上下游** | 上游：Context.assemble()；下游：Execute/Tool Loop。 |
| **可扩展点** | 实现 IModelAdapter；自定义 IModelAdapterManager。 |

---

# P3：Example 05 如何使用框架搭建 Agent 应用

## 3.1 文件结构（example05 实际）

```
05-dare-coding-agent-enhanced/
├── main.py
├── cli.py               # 交互式 CLI + Builder 组装
├── local_mcp_server.py  # 本地 MCP HTTP 服务（四则运算）
├── a2a_serve.py         # A2A Server 示例
├── a2a_client_demo.py   # A2A Client 示例
├── README.md
├── validators/
│   └── file_validator.py  # FileExistsValidator
├── workspace/           # 工作目录
├── demo.py
└── demo_script.txt
```

> 注：FileConfigProvider 会在 workspace/user 目录创建/读取 `.dare/config.json`（若不存在）。

## 3.2 Builder 组装代码（cli.py _create_builder）

```python
# 1. 创建 Model
model = OpenRouterModelAdapter(
    model=model_name,
    api_key=api_key,
    extra={"max_tokens": max_tokens},
    http_client_options={"timeout": timeout_seconds},
)

# 2. Knowledge（rawdata 内存）
knowledge = RawDataKnowledge(storage=InMemoryRawDataStorage())

# 3. 本地工具
tools = [ReadFileTool(), WriteFileTool(), SearchCodeTool(), RunCommandTool()]

# 4. Validator
validator = FileExistsValidator(workspace=workspace, expected_files=[], verbose=False)

# 5. EventLog（用于 CLI 展示）
event_log = StreamingEventLog(display.show_event)

# 6. RunContext 工厂（传入 workspace）
run_context_factory = lambda: RunContext(
    metadata={"agent": "dare-coding-agent"},
    config={"workspace_roots": [str(workspace)]},
)

# 7. Builder 组装
builder = (
    DareAgentBuilder("dare-coding-agent")
    .with_model(model)
    .with_knowledge(knowledge)
    .add_tools(*tools)
    .with_run_context_factory(run_context_factory)
    .with_planner(DefaultPlanner(model, verbose=False))
    .add_validators(validator)
    .with_remediator(DefaultRemediator(model, verbose=False))
    .with_event_log(event_log)
)

# 8. Config（含 mcp_paths、skill_mode 等）
if config is not None:
    builder = builder.with_config(config)

# 9. 异步 build（内部会加载 MCP）
agent = await builder.build()
```

## 3.3 执行流程（CLI 视角）

1. **main()** 解析参数，加载 FileConfigProvider → builder.build()。
2. **plan 模式**：preview_plan() 调用 DefaultPlanner.plan()，输出计划并等待 `/approve`。
3. **execute 模式**：`agent.run(Task(description=...))` 直接执行。
4. **StreamingEventLog**：append 时回调 display.show_event() 展示 plan/tool/milestone 事件。

## 3.4 FileExistsValidator 与 Plan 的衔接

- DefaultPlanner 输出 ProposedPlan（steps 中 capability_id 为 evidence 类型）。
- FileExistsValidator.validate_plan 将 ProposedStep 转 ValidatedStep（risk_level=READ_ONLY）。
- verify_milestone 从 plan.steps 的 params.expected_files 收集文件列表 → 检查 workspace 文件存在性。

---

# P4：Agent 模块设计

## 4.1 接口定义（agent/kernel.py, interfaces.py）

- **IAgent**：`async def run(task: str | Task, deps) -> RunResult`
- **IAgentOrchestration**：`async def execute(task: Task, deps) -> RunResult`

## 4.2 DareAgent 编排流程图（更新版）

```
run(task)
  │
  ▼
execute(task) ──► 模式判断
  │
  ├─ [Five-Layer] ─► _run_session_loop(task)
  │       │
  │       ├─► config_snapshot (IConfigProvider) + context.config_update
  │       ├─► previous_session_summary → system_message
  │       ├─► milestones = task.milestones ? planner.decompose() ? task.to_milestones()
  │       │
  │       ├─► FOR each milestone:
  │       │      ├─► PlanAttemptSandbox.create_snapshot(STM)
  │       │      ├─► _run_plan_loop(milestone)
  │       │      │      planner.plan → validator.validate_plan
  │       │      ├─► _run_execute_loop(validated_plan)
  │       │      │      context.assemble → model.generate → tool_calls → _run_tool_loop
  │       │      │      plan_tool? → rollback snapshot, continue
  │       │      ├─► _verify_milestone(execute_result, validated_plan)
  │       │      ├─► success → sandbox.commit
  │       │      └─► fail → sandbox.rollback + remediator.remediate() → reflection
  │       │
  │       └─► SessionSummary → (optional) ISessionSummaryStore.save
  │
  ├─ [ReAct] ─► _run_react_loop(task)
  │       user_message → stm_add
  │       _run_execute_loop(None)
  │
  └─ [Simple] ─► _run_simple_loop(task)
          user_message → stm_add
          context.assemble → model.generate

return RunResult(success, output, errors, session_id, session_summary?)
```

### 4.2.1 DareAgent 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | `Task(description, task_id?, milestones?, previous_session_summary?)`。 |
| **输出** | `RunResult(success, output, errors, session_id, session_summary)`。 |
| **模式选择** | 有 planner 或 task.milestones → Five-Layer；无 planner 有 tool_gateway → ReAct；否则 Simple。 |
| **Session 循环** | 配置快照 + summary 注入；milestone 来源：task.milestones / planner.decompose / task.to_milestones。 |
| **Milestone 循环** | PlanAttemptSandbox snapshot/rollback；Plan → Execute → Verify；失败时 Remediator 反思。 |
| **Execute 循环** | context.assemble → model.generate → tool_calls → _run_tool_loop；无 tool_calls 直接结束。 |
| **Tool Loop** | Budget + Hook + EventLog；记录 evidence 并写入 milestone_state。 |
| **与上下游** | 上游：Builder 注入 model/context/planner/validator/remediator/tool_gateway/event_log/hooks/telemetry。下游：Context/Model/ToolManager/Validator/Remediator。 |
| **可扩展点** | IAgentOrchestration、IPlanAttemptSandbox、ExecutionControl、HookPhase。 |

## 4.3 Builder 工作逻辑图与解析顺序（builder.py）

```
build() [async]
    │
    ├─► if config.mcp_paths: load_mcp_toolkit() → MCPToolkit.initialize()
    │
    ├─► (auto_skill_mode?) load SkillStore + inject SearchSkillTool/SkillScriptRunner
    │
    ├─► _resolved_tools() = explicit + auto_skill + MCP + manager_tools
    │
    ├─► manager = _ensure_tool_manager(tools)
    ├─► _register_tools_with_manager(manager, tools)
    │       + knowledge_get/knowledge_add
    │
    ├─► tool_gateway = _ensure_tool_gateway(tools)
    ├─► tool_provider = _ensure_tool_provider(manager, tools)
    │
    ├─► _resolve_sys_prompt(model)
    │       prompt_id = override | config.default_prompt_id | "base.system"
    │       store = LayeredPromptStore(workspace+user+builtin)
    │
    ├─► context = Context(...) 或 _apply_context_overrides
    │       context._tool_provider = tool_provider
    │       context._sys_prompt = sys_prompt (+skill content)
    │
    └─► 构造 Agent（Dare/React/SimpleChat）
            planner/validator/remediator/hooks/telemetry/config_provider 等注入
```

### 4.3.1 Builder 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | with_model / add_tools / with_knowledge / with_long_term_memory / with_planner / add_validators / with_remediator / with_event_log / with_config / with_telemetry ... |
| **输出** | Agent 实例（DareAgent/ReactAgent/SimpleChatAgent）。 |
| **工具解析顺序** | explicit → auto_skill tools → MCP → manager.load_tools → 注册 ToolManager。 |
| **Prompt 解析** | prompt_id override → config.default_prompt_id → "base.system"；LayeredPromptStore。 |
| **Skill 挂载** | persistent_skill_mode：初始 skill 直接合并；auto_skill_mode：只注入摘要 + search_skill 工具。 |
| **与上下游** | 上游：Config/Managers；下游：Context/ToolManager/Agent。 |
| **可扩展点** | 继承 _BaseAgentBuilder，实现 _build_impl()；自定义 Manager。 |

## 4.4 ReactAgent 编排流程图

```
_execute(task)
    │
    ├─► user_message → stm_add
    ├─► FOR round in range(max_tool_rounds):
    │       assembled = context.assemble()
    │       model_input = ModelInput(messages, tools)
    │       response = await model.generate(model_input)
    │       budget_use + budget_check
    │
    │       IF no tool_calls: assistant_message → stm_add → return content
    │       IF no gateway.invoke: return "Tool calls not executed"
    │
    │       assistant_msg(metadata.tool_calls) → stm_add
    │       FOR each tool_call: gateway.invoke(name, params, Envelope()) → tool_msg → stm_add
    │       reassemble → next round
    │
    └─► return "Reached max tool rounds..."
```

### 4.4.1 ReactAgent 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | task: str；构造时需 model、context、tools、max_tool_rounds。 |
| **输出** | str：最终 response.content 或超限提示。 |
| **关键步骤** | assemble → model.generate → tool_calls → gateway.invoke → tool_msg → reassemble。 |
| **与 DareAgent 差异** | 无 Session/Milestone/Plan/Verify；无 event_log/hooks。 |
| **可扩展点** | 继承 ReactAgent 覆写 _execute；调整 max_tool_rounds。 |

## 4.5 SimpleChatAgent 工作逻辑图

```
_execute(task)
    │
    ├─► user_message → stm_add
    ├─► assembled = context.assemble()
    ├─► model_input = ModelInput(messages, tools)
    ├─► response = model.generate()
    ├─► assistant_message → stm_add
    └─► return response.content
```

### 4.5.1 SimpleChatAgent 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | task: str；model + context。 |
| **输出** | response.content。 |
| **关键步骤** | 无工具循环，单次模型调用。 |
| **与上下游** | 上游：SimpleChatAgentBuilder；下游：Context/Model。 |
| **可扩展点** | 自定义 Context 或 ModelAdapter。 |

---

# P5：Context 模块设计

## 5.1 接口（context/kernel.py）

- **IRetrievalContext**：`get(query, **kwargs) -> list[Message]`
- **IContext**：id, short_term_memory, long_term_memory, knowledge, budget, toollist, config；stm_add/stm_get；budget_use/check/remaining；listing_tools；assemble；compress；config_update

## 5.2 assemble() 工作逻辑图（含 auto_skill_mode）

```
assemble()
    │
    ├─► messages = stm_get()
    ├─► tools = listing_tools()  // list_tool_defs 优先
    ├─► sys_prompt = _sys_prompt
    ├─► for skill in _loaded_full_skills (auto_skill_mode):
    │       sys_prompt = enrich_prompt_with_skill(sys_prompt, skill)
    └─► return AssembledContext(messages, sys_prompt, tools, metadata={"context_id": id})
```

### 5.2.1 Context 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | stm_add(message)、budget_use、set_skill/add_loaded_full_skill。 |
| **输出** | AssembledContext(messages, sys_prompt, tools, metadata)。 |
| **关键步骤** | listing_tools 优先用 ToolManager.list_tool_defs；auto_skill_mode 动态合并 skill。 |
| **与上下游** | 上游：Builder 注入 tool_provider/sys_prompt/skill；下游：ModelInput。 |
| **可扩展点** | 覆写 assemble() 以自定义 LTM/Knowledge 拼接策略。 |

## 5.3 Budget（context/types.py）工作逻辑与要点

| 项目 | 说明 |
|------|------|
| **字段** | max_tokens, max_cost, max_time_seconds, max_tool_calls；used_tokens, used_cost, used_time_seconds, used_tool_calls。 |
| **budget_use()** | 按资源名累加 used_*。 |
| **budget_check()** | 任一 used_* > max_* 则 raise RuntimeError。 |
| **budget_remaining()** | 返回剩余预算（未设则 inf）。 |

---

# P6：Plan 模块设计

## 6.1 类型（plan/types.py）

- Task：description, task_id, milestones, metadata, previous_session_summary, resume_from_checkpoint
- Milestone：milestone_id, description, user_input, success_criteria
- DecompositionResult：milestones, reasoning
- ProposedPlan：plan_description, steps, attempt, metadata
- ProposedStep：step_id, capability_id, params, description, envelope
- ValidatedPlan：plan_description, steps, success, errors, metadata
- ValidatedStep：step_id, capability_id, risk_level, params, description, envelope, metadata
- VerifyResult：success, errors, evidence_required/evidence_collected
- Envelope：allowed_capability_ids, budget, done_predicate, risk_level
- DonePredicate：required_keys, description
- ToolLoopRequest：capability_id, params, envelope
- RunResult：success, output, errors, metadata, session_id, session_summary

## 6.2 DefaultPlanner 工作逻辑图

```
plan(ctx)
    │
    ├─► task_description = ctx.stm_get()[-1].content
    ├─► user_prompt = "Task: ... Output ONLY valid JSON ..."
    ├─► model_input = ModelInput(system+user)
    ├─► response = await model.generate(model_input)
    ├─► plan_data = _parse_response(content)
    ├─► steps = ProposedStep(...)
    └─► return ProposedPlan(plan_description, steps)
```

**decompose()**：默认返回单 milestone；可覆写实现 LLM 拆解。

### 6.2.1 DefaultPlanner 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | ctx: IContext（任务来自 STM 最后一条消息）。 |
| **输出** | ProposedPlan(plan_description, steps)。 |
| **关键步骤** | system+user prompt → model.generate → JSON parse → ProposedStep。 |
| **与上下游** | 上游：DareAgent _run_plan_loop；下游：Validator.validate_plan。 |
| **可扩展点** | 覆写 plan/_parse_response/_fallback_plan；实现 decompose()。 |

## 6.3 IValidator / CompositeValidator

```
validate_plan(plan, ctx)
    FOR validator in validators:
        plan = validator.validate_plan(plan)
        IF not plan.success: return plan

verify_milestone(result, ctx, plan?)
    FOR validator in validators:
        verify = validator.verify_milestone(...)
        IF not verify.success: return verify
```

### 6.3.1 IValidator 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | validate_plan(ProposedPlan, ctx)；verify_milestone(RunResult, ctx, plan?)。 |
| **输出** | ValidatedPlan / VerifyResult。 |
| **关键步骤** | CompositeValidator 顺序执行，失败即返回。 |
| **与上下游** | 上游：Plan Loop；下游：Execute/Verify 决策。 |
| **可扩展点** | 自定义 IValidator（如 file/quality/security）。 |

## 6.4 DefaultRemediator 工作逻辑图

```
remediate(verify_result, ctx)
    │
    ├─► errors + recent STM → user_prompt
    ├─► ModelInput(system+user)
    ├─► response = model.generate()
    └─► return response.content (reflection)
```

### 6.4.1 DefaultRemediator 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | VerifyResult + Context。 |
| **输出** | 反思文本（Failure Analysis / Adjustments）。 |
| **关键步骤** | 拼 prompt → model.generate → 返回文本。 |
| **与上下游** | 上游：DareAgent 在 milestone 失败后调用；下游：reflection 写入 milestone_state。 |
| **可扩展点** | 自定义 remediate 或 system_prompt。 |

## 6.5 PlanAttemptSandbox（DefaultPlanAttemptSandbox）

```
create_snapshot(ctx) → snapshot_id
rollback(ctx, snapshot_id) → STM 清空并恢复
commit(snapshot_id) → 丢弃快照
```

### 6.5.1 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | Context（STM）。 |
| **输出** | snapshot_id；rollback/commit 控制 STM 状态。 |
| **关键步骤** | STM 快照复制；失败回滚避免污染上下文。 |
| **与上下游** | 上游：DareAgent _run_milestone_loop；下游：Plan/Execute/Verify。 |
| **可扩展点** | 自定义 IPlanAttemptSandbox（可持久化）。 |

---

# P7：Tool 模块设计

## 7.1 接口（tool/kernel.py, interfaces.py, types.py）

- **IToolGateway**：list_capabilities(), invoke(capability_id, params, envelope)
- **IToolManager**：注册/更新/禁用工具、list_tool_defs
- **ITool**：name, description, input_schema, output_schema, risk_level, requires_approval, capability_kind, execute()
- **IToolProvider**：list_tools()
- **RunContext**：deps, run_id, task_id, milestone_id, metadata, config
- **CapabilityDescriptor**：id, name, description, metadata（risk_level/approval/is_work_unit）

## 7.2 ToolManager 工作逻辑图

```
register_tool(tool)
    ├─► capability_id = tool.name
    ├─► _descriptor_from_tool → CapabilityDescriptor(metadata含risk/approval/kind)
    └─► 写入 _registry

list_tool_defs()
    └─► 返回 OpenAI function 格式 + metadata + capability_id

invoke(capability_id, params, envelope)
    ├─► allowed_capability_ids 校验
    ├─► entry = _registry[capability_id]
    └─► entry.tool.execute(params, context_factory())
```

### 7.2.1 ToolManager 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | register_tool(ITool) / invoke(capability_id, params, envelope)。 |
| **输出** | CapabilityDescriptor / ToolResult(success, output, error, evidence)。 |
| **关键步骤** | 生成 CapabilityDescriptor；list_tool_defs 输出模型可用 tool schema。 |
| **与上下游** | 上游：Builder 注册工具；下游：ModelInput.tools / Tool Loop。 |
| **可扩展点** | 实现 IToolManager 或注册 IToolProvider。 |

## 7.3 MCPToolkit 工作逻辑图

```
initialize()
    FOR client in clients:
        connect → list_tools
        full_name = "{client}:{tool}"
        _tools[full_name] = MCPTool(...)
```

### 7.3.1 MCPToolkit / MCPTool 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | MCPToolkit(clients)、MCPTool.execute(input, context)。 |
| **输出** | MCPTool 列表；ToolResult 来自 client.call_tool。 |
| **关键步骤** | connect → list_tools → 包装为 ITool。 |
| **可扩展点** | 新 transport / 自定义 IMCPClient。 |

## 7.4 工具调用链路工作逻辑图（DareAgent → ToolManager）

```
_run_tool_loop(ToolLoopRequest)
    │
    ├─► budget_check + budget_use("tool_calls",1)
    ├─► BEFORE_TOOL hook + event_log.append("tool.invoke")
    ├─► tool_gateway.invoke(capability_id, params, envelope)
    │       └─► ToolManager → tool.execute(params, context)
    ├─► event_log.append("tool.result")
    ├─► IF result.evidence: milestone_state.add_evidence(...)
    └─► AFTER_TOOL hook → return success/output/error
```

### 7.4.1 工具调用链路要点说明

| 项目 | 说明 |
|------|------|
| **输入** | ToolLoopRequest(capability_id, params, envelope)。 |
| **输出** | dict：success/output/error/result。 |
| **关键步骤** | envelope 权限与预算控制；证据 evidence 写入 milestone_state。 |
| **与上下游** | 上游：Execute Loop；下游：ITool.execute/MCPTool.execute。 |
| **可扩展点** | ExecutionControl + requires_approval + HumanApprovalRequired。 |

---

# P8：Knowledge 模块设计

## 8.1 接口（knowledge/kernel.py, knowledge_tools.py）

- **IKnowledge**：get(query, **kwargs) -> list[Message]；add(content, **kwargs)
- **KnowledgeGetTool**：name="knowledge_get"；execute 调用 knowledge.get
- **KnowledgeAddTool**：name="knowledge_add"；execute 调用 knowledge.add

## 8.2 RawDataKnowledge 工作逻辑图

```
add(content, metadata)
    storage.add(content, metadata)

get(query, top_k)
    records = storage.search(query, top_k)
    return Message(role="assistant", content=record.content, metadata=...)
```

### 8.2.1 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | add(content, metadata?)；get(query, top_k?)。 |
| **输出** | get 返回 Message 列表。 |
| **关键步骤** | substring 检索（IRawDataStore）。 |
| **与上下游** | 上游：Builder/Config；下游：knowledge_get/knowledge_add。 |
| **可扩展点** | 自定义存储（sqlite/in_memory）。 |

## 8.3 VectorKnowledge 工作逻辑图与要点

```
add(content)
    embed → vector_store.add

get(query)
    embed query → vector_store.search → Message + similarity
```

| 项目 | 说明 |
|------|------|
| **输入** | embedding_adapter + vector_store。 |
| **输出** | Message 列表，metadata 含 similarity。 |
| **可扩展点** | 替换 IEmbeddingAdapter 或 IVectorStore。 |

---

# P9：Model 模块设计

## 9.1 接口（model/kernel.py）

- **IModelAdapter**：generate(model_input) -> ModelResponse
- **ModelInput**：messages, tools, metadata
- **ModelResponse**：content, tool_calls, usage

## 9.2 OpenRouterModelAdapter 工作逻辑图

```
_generate(model_input, options?)
    client = AsyncOpenAI(api_key, base_url)
    messages = _serialize_messages()
    api_params = {model, messages, tools?, extra?, options?}
    response = client.chat.completions.create(**api_params)
    return ModelResponse(content, tool_calls, usage)
```

### 9.2.1 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | OpenRouter API + OpenAI SDK；http_client_options 支持超时等。 |
| **输出** | ModelResponse(content, tool_calls, usage)。 |
| **关键步骤** | _serialize_messages 转 OpenAI 格式；_extract_tool_calls 解析工具调用。 |
| **可扩展点** | 自定义 base_url/extra 参数。 |

## 9.3 OpenAIModelAdapter（LangChain）要点

- 使用 ChatOpenAI（langchain-openai），支持自定义 endpoint
- tools 通过 bind_tools 绑定
- response.tool_calls / response_metadata.token_usage 解析为 ModelResponse

## 9.4 Prompt 解析工作逻辑图与要点（builder._resolve_sys_prompt）

```
_resolve_sys_prompt(model)
    IF with_prompt: return prompt
    prompt_id = override | config.default_prompt_id | "base.system"
    store = LayeredPromptStore(workspace + user + builtin)
    return store.get(prompt_id, model=model.name)
```

---

# P10：Memory 模块设计

## 10.1 InMemorySTM 工作逻辑图

```
add(message) → _messages.append
get() → list(_messages)
compress(max_messages) → 仅保留最近 N 条
```

### 10.1.1 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | add/get/clear/compress。 |
| **输出** | Message 列表。 |
| **可扩展点** | 替换为持久化 STM。 |

## 10.2 LongTermMemory（RawData/Vector）工作逻辑图

```
RawDataLongTermMemory.get(query)
    storage.search → Message

VectorLongTermMemory.get(query)
    embed(query) → vector_store.search → Message + similarity

persist(messages)
    rawdata: storage.add
    vector: embed_batch → vector_store.add_batch
```

### 10.2.1 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | long_term_memory 配置或实例。 |
| **输出** | get(query) → Message 列表。 |
| **关键步骤** | Vector LTM 依赖 embedding_adapter。 |
| **可扩展点** | 新存储后端或检索策略。 |

---

# P11：Event、Hook、Observability、Config

## 11.1 IEventLog 与 TraceAwareEventLog

**工作逻辑图**：

```
DareAgent._log_event()
    └─► make_trace_aware(event_log).append(event_type, payload)
           └─► payload 加 _trace(trace_id/span_id)
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | append(event_type, payload)。 |
| **输出** | event_id；可 query/replay/verify_chain。 |
| **关键步骤** | TraceAwareEventLog 自动附加 trace context。 |
| **可扩展点** | WORM/哈希链/远程存储。 |

## 11.2 IHook / HookExtensionPoint

```
emit(phase, payload)
    callbacks(同步) → hooks.invoke(异步)
```

**HookPhase**：BEFORE/AFTER_RUN, SESSION, MILESTONE, PLAN, EXECUTE, CONTEXT_ASSEMBLE, MODEL, TOOL, VERIFY 等。

## 11.3 Observability（Telemetry + ObservabilityHook）

**工作逻辑图**：

```
DareAgent (HookPhase.*)
    └─► ObservabilityHook
          ├─► start_span / end_span
          ├─► record_metric
          └─► 采集 token_usage / budget / tool_calls
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | Hook payload（token_usage, budget_stats, duration）。 |
| **输出** | Traces/Metrics/Logs（OTel）。 |
| **关键步骤** | BEFORE_RUN/AFTER_RUN span + milestone/plan/execute/tool spans。 |
| **可扩展点** | 自定义 ITelemetryProvider；配置 ObservabilityConfig。 |

## 11.4 Config（config/types.py）

**核心字段**：
- llm（adapter, endpoint, api_key, model, proxy, extra）
- mcp / mcp_paths / allowmcps
- tools / components.disabled
- knowledge / long_term_memory
- prompt_store_path_pattern / default_prompt_id
- skill_mode / initial_skill_path / skill_paths
- observability（OTLP/exporter/采样/脱敏）
- a2a（AgentCard 配置）

**FileConfigProvider**：合并 user + workspace 两层 `.dare/config.json`。默认会创建空配置文件。

---

# P12：MCP 模块设计

## 12.1 配置加载工作逻辑图

```
load_mcp_configs(paths, workspace_dir, user_dir)
    └─► MCPConfigLoader(paths).load()
          ├─► scan .json/.yaml/.yml/.md
          └─► MCPServerConfig.from_dict
```

### 12.1.1 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | paths 或 Config.mcp_paths（相对 workspace_dir）。 |
| **输出** | MCPServerConfig 列表。 |
| **关键步骤** | 支持多服务器定义；stdio/http/grpc 类型解析。 |
| **可扩展点** | 新 transport/解析格式。 |

## 12.2 客户端创建与 MCPTool 调用工作逻辑图

```
create_mcp_clients(configs)
    ├─► stdio → StdioTransport
    ├─► http  → HTTPTransport
    └─► grpc  → 未实现（抛错）

MCPTool.execute(input, context)
    └─► client.call_tool(tool_name, input, context)
```

---

# P13：Skill 模块设计

## 13.1 FileSystemSkillLoader 工作逻辑图

```
load()
    ├─► _iter_skill_dirs(root)
    ├─► parse SKILL.md (frontmatter + body)
    ├─► scripts/ 读取 → {name: path}
    └─► Skill(id, name, content, scripts)
```

### 13.1.1 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | skills 目录或 SKILL.md 所在目录。 |
| **输出** | list[Skill]。 |
| **关键步骤** | 递归扫描 → parse_skill_md → scripts 映射。 |
| **可扩展点** | ISkillLoader/解析规则。 |

## 13.2 SkillStore 与 Auto Skill 模式

```
SkillStore(loader)
    ├─► load() → list_skills()
    └─► select_for_task(task_description)  // 可选 selector
```

**SearchSkillTool**：根据 skill_id 将完整 Skill 注入 Context；assemble() 会合并进 sys_prompt。

**SkillScriptRunner**：统一入口 run_skill_script(skill_id, script_name, args)，支持证据回传与审批。

---

# P14：A2A 协议适配（Agent-to-Agent）

## 14.1 A2A Server 逻辑图（JSON-RPC）

```
create_a2a_app(card, agent.run)
    ├─► GET /.well-known/agent.json → AgentCard
    ├─► POST / JSON-RPC
    │     ├─► tasks/send → agent.run(Task) → RunResult → Artifact
    │     ├─► tasks/get  → 返回 TaskState
    │     ├─► tasks/cancel → 标记 cancelled
    │     └─► tasks/sendSubscribe → SSE streaming
    └─► GET /a2a/artifacts/{task_id}/{filename} → 文件附件
```

## 14.2 Message/Artifact 适配要点

| 项目 | 说明 |
|------|------|
| **输入** | A2A Message.parts（text/file）。 |
| **转换** | text 拼接为 Task.description；file 可解码为本地附件并写入 metadata。 |
| **输出** | RunResult 转 A2A Artifact（文本 + file inline/URI）。 |
| **关键步骤** | inlineData base64 解码；大文件落盘 `.a2a_artifacts` 并生成 URI。 |
| **可扩展点** | 自定义附件策略或 auth_validate。 |

## 14.3 A2A Client 运行流程（示例）

```
client.discover_agent_card(base_url)
client.send_async(message)
    └─► tasks/send → TaskState + artifacts
```

---

*文档完。所有内容均从 dare_framework 与 examples/05-dare-coding-agent-enhanced 源码推导，用于生成 PPT 与流程图。*
