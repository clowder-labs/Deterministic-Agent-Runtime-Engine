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
│  │ DareAgentBuilder | ReactAgentBuilder | ChatAgentBuilder                    │  │
│  │ 链式配置：with_model / add_tools / with_knowledge / with_planner / ...      │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 2: 编排层（Agent 实现）                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   DareAgent     │  │   ReactAgent    │  │   ChatAgent     │                  │
│  │ Dare 编排       │  │ ReAct 工具循环  │  │ 纯对话无工具     │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 1: 核心域组件（可插拔）                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Context  │ │  Model   │ │   Plan   │ │   Tool   │ │Knowledge │ │  Memory  │  │
│  │ 上下文   │ │ 模型适配 │ │ 计划校验 │ │ 工具调用 │ │ 知识库   │ │ 记忆     │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                            │
│  │  Event   │ │   Hook   │ │  Config  │ │   MCP    │                            │
│  │ 事件日志 │ │ 扩展点   │ │ 配置     │ │ 协议适配 │                            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Layer 0: 边界与基础设施                                                          │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │ IToolGateway        │  │ IEventLog           │  │ IExecutionControl   │      │
│  │ 工具调用单一边界    │  │ 审计/可重放         │  │ HITL 控制           │      │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 1.2 各层组件清单与扩展方向（源码依据）

| 层级 | 组件 | 源码路径 | 扩展方式 |
|------|------|----------|----------|
| **L3 Builder** | DareAgentBuilder | agent/_internal/builder.py | 继承 _BaseAgentBuilder，实现 _build_impl() |
| **L3 Builder** | ReactAgentBuilder | agent/_internal/builder.py | 同上 |
| **L3 Builder** | ChatAgentBuilder | agent/_internal/builder.py | 同上 |
| **L2 编排** | DareAgent | agent/_internal/five_layer.py | 实现 IAgentOrchestration，或新增编排策略 |
| **L2 编排** | ReactAgent | agent/_internal/react_agent.py | 同上 |
| **L2 编排** | ChatAgent | agent/_internal/simple_chat.py | 同上 |
| **L1 Context** | Context | context/_internal/context.py | 实现 IContext，可覆写 assemble() |
| **L1 Model** | OpenRouterModelAdapter | model/_internal/openrouter_adapter.py | 实现 IModelAdapter.generate() |
| **L1 Plan** | DefaultPlanner | plan/_internal/default_planner.py | 实现 IPlanner.plan() |
| **L1 Plan** | IValidator 实现 | plan/interfaces.py | 实现 validate_plan()、verify_milestone() |
| **L1 Plan** | DefaultRemediator | plan/_internal/default_remediator.py | 实现 IRemediator.remediate() |
| **L1 Tool** | ToolManager | tool/_internal/managers/tool_manager.py | 实现 IToolManager，或注册 IToolProvider |
| **L1 Tool** | Native Tools | tool/_internal/tools/*.py | 实现 ITool（name, input_schema, execute 等） |
| **L1 Knowledge** | RawDataKnowledge | knowledge/_internal/rawdata_knowledge/ | 实现 IKnowledge.get/add |
| **L1 Knowledge** | VectorKnowledge | knowledge/_internal/vector_knowledge/ | 同上 |
| **L1 Memory** | InMemorySTM | memory/_internal/in_memory_stm.py | 实现 IShortTermMemory（add/get/clear/compress） |
| **L1 Event** | IEventLog 实现 | event/kernel.py | 实现 append/query/replay/verify_chain |
| **L1 Hook** | IHook 实现 | hook/kernel.py | 实现 invoke(phase, ...) |
| **L1 Config** | Config | config/types.py | 扩展 Config 字段，或实现 IConfigProvider |
| **L1 MCP** | MCPToolkit | tool/_internal/toolkits/mcp_toolkit.py | 新增 transport（如 gRPC）或新 MCP 客户端 |

## 1.3 数据流总览（可用于画图）

```
User Task (str | Task)
        │
        ▼
   IAgent.run()
        │
        ├─► [Dare Agent] Session → Milestone → Plan → Execute → Tool
        ├─► [ReAct] Execute → Tool (无 Plan)
        └─► [Chat] 单次 model.generate()
        │
        ▼
   RunResult(success, output, errors)
```

---

# P2：框架支持的外部挂载

## 2.1 MCP（Model Context Protocol）

**挂载方式**：
- Config.mcp_paths 指定配置目录（如 `.dare/mcp/`）
- Builder.build() 时自动调用 load_mcp_toolkit()，扫描目录下 JSON/YAML/MD
- 支持 transport：stdio、http（gRPC 未实现）

**配置格式**（源码 mcp/types.py, loader.py）：
```json
{
  "name": "local_math",
  "transport": "http",
  "url": "http://127.0.0.1:8765/",
  "timeout_seconds": 30
}
```

**流程**：load_mcp_configs → create_mcp_clients → MCPToolkit.initialize() → list_tools() 返回 MCPTool 列表，工具名格式 `server:tool`（如 `local_math:add`）

**过滤**：Config.allowmcps 可限制启用的 MCP 服务器列表。

## 2.2 Skill（Agent Skills 格式）

**挂载方式**：
- Builder.with_skill(path) 或 Config.initial_skill_path
- 运行时 agent.set_skill(skill) / agent.clear_skill()

**目录结构**（源码 skill/_internal/filesystem_skill_loader.py）：
```
my_skill/
├── SKILL.md        # YAML frontmatter + markdown 正文
└── scripts/        # 可执行脚本
    ├── run_tool.py
    └── check.sh
```

**注入时机**：Context.assemble() 时，enrich_prompt_with_skill() 将 skill.content 和 scripts 列表追加到 sys_prompt。

**限制**：同一时刻仅支持一个 skill。

## 2.3 Knowledge 库

**挂载方式**：
- Builder.with_knowledge(knowledge) 显式注入
- 或 Config.knowledge + with_embedding_adapter（用于 vector 类型）

**类型**（源码 knowledge/factory.py）：
- **rawdata**：RawDataKnowledge，无 embedding，substring 检索；storage 可选 in_memory | sqlite
- **vector**：VectorKnowledge，需 IEmbeddingAdapter；storage 可选 in_memory | sqlite | chromadb

**工具暴露**：框架自动注册 knowledge_get、knowledge_add 到 ToolManager，Agent 可像调用普通工具一样调用。

## 2.4 本地 Tools

**挂载方式**：Builder.add_tools(*tools)，每个 tool 需实现 ITool。

**内置工具**（tool/_internal/tools/）：read_file、write_file、search_code、run_command、edit_line、echo、noop 等。

## 2.5 Hook（扩展点）

**挂载方式**：
- **DareAgent**：DareAgentBuilder.add_hooks(*hooks)，每个 hook 需实现 IHook
- 或通过 with_managers(hook_manager=...) 注入 IHookManager，Builder 在 build 时从 manager.load_hooks(config) 解析并与显式 add_hooks 合并
- 仅 DareAgent 支持 hooks；ReactAgent / SimpleChatAgent 无 HookExtensionPoint

**接口**（源码 hook/kernel.py, types.py）：
- **IHook**：`async def invoke(phase: HookPhase, *args, **kwargs) -> Any`；best-effort，失败不中断主流程
- **HookPhase**：BEFORE_RUN, AFTER_RUN, BEFORE_SESSION, AFTER_SESSION, BEFORE_MILESTONE, AFTER_MILESTONE, BEFORE_PLAN, AFTER_PLAN, BEFORE_EXECUTE, AFTER_EXECUTE, BEFORE_CONTEXT_ASSEMBLE, AFTER_CONTEXT_ASSEMBLE, BEFORE_MODEL, AFTER_MODEL, BEFORE_TOOL, AFTER_TOOL, BEFORE_VERIFY, AFTER_VERIFY
- **IExtensionPoint**：register_hook(phase, callback: HookFn)、async emit(phase, payload)

**工作逻辑图**：

```
DareAgent 构造
    hooks = 显式 add_hooks + hook_manager.load_hooks(config) 合并
    _extension_point = HookExtensionPoint(hooks) if hooks else None

运行时 _emit_hook(phase, payload)
    IF _extension_point is None: return
    enriched = {**payload, "phase": phase.value, ...}  // 可选注入 run_id 等
    await _extension_point.emit(phase, enriched)
        │
        ├─► FOR each callback in _callbacks.get(phase, []): callback(payload)  // 同步，异常仅 log
        └─► FOR each hook in _hooks: await hook.invoke(phase, payload=payload)    // 异步，异常仅 log
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | add_hooks(*hooks: IHook)；invoke(phase, payload) 的 payload 由 Agent 在各阶段传入（如 task_id, run_id, iteration, model_usage, budget_stats, milestone_id）。 |
| **输出** | 无返回值要求；best-effort，单 hook 异常仅打 log，不中断 execute。 |
| **关键步骤** | Builder 将显式 hooks 与 hook_manager 解析结果合并，DareAgent 持有一个 HookExtensionPoint(hooks)。运行时在 Session/Milestone/Plan/Execute/Model/Tool/Verify 前后调用 _emit_hook(phase, payload)；emit 先执行 register_hook 的 callbacks，再顺序执行各 IHook.invoke。 |
| **与上下游** | 上游：DareAgentBuilder.add_hooks() 或 with_managers(hook_manager)；Config.components 可控制启用。下游：ObservabilityHook 向 ITelemetryProvider 上报；自定义 Hook 可做审计、审批、指标、日志。 |
| **可扩展点** | 实现 IHook.invoke(phase, *args, **kwargs)；或 register_hook(phase, callback) 注册同步函数；HookPhase 覆盖全生命周期，payload 结构按阶段扩展。 |

## 2.6 模型（Model）

**挂载方式**：
- **显式**：Builder.with_model(model)，model 需实现 IModelAdapter
- **Config 驱动**：with_managers(model_adapter_manager=...) 注入 IModelAdapterManager，Builder 在 _resolved_model() 时若未显式 with_model 则调用 manager.load_model_adapter(config)

**接口**（源码 model/kernel.py）：
- **IModelAdapter**：`async def generate(model_input: ModelInput, *, options: GenerateOptions | None) -> ModelResponse`
- **ModelInput**：messages, tools?, metadata
- **ModelResponse**：content, tool_calls?, usage?, metadata

**内置实现**（源码 model/_internal/）：
- **OpenRouterModelAdapter**：OpenRouter API（OpenAI 兼容），base_url、api_key、model、extra 可配
- **OpenAIModelAdapter**：OpenAI API 直连

**工作逻辑图**：

```
Builder._resolved_model()
    IF _model is not None: return _model
    manager = _model_adapter_manager or create_default_model_adapter_manager(_manager_config())
    return manager.load_model_adapter(config=...)  // 单例，仅一个 Model 生效

运行时（Plan / Execute / Simple）
    assembled = context.assemble()
    model_input = ModelInput(messages=assembled_messages, tools=assembled.tools, metadata=assembled.metadata)
    response = await model.generate(model_input, options?)
    // 使用 response.content、response.tool_calls、response.usage 写 STM、跑工具、计 budget
```

**要点说明**：

| 项目 | 说明 |
|------|------|
| **输入** | with_model(IModelAdapter) 或由 IModelAdapterManager.load_model_adapter(config) 返回。generate(model_input, options?)：ModelInput(messages, tools?, metadata)；options 含 temperature, max_tokens, top_p, stop。 |
| **输出** | ModelResponse(content, tool_calls, usage, metadata)。Agent 用 content 写 assistant_message 入 STM；tool_calls 驱动 _run_tool_loop；usage 用于 budget_use("tokens") 与观测。 |
| **关键步骤** | 显式 with_model 优先；否则从 model_adapter_manager 按 config 加载。调用链：context.assemble() → ModelInput → model.generate() → 解析 content/tool_calls/usage。OpenRouterModelAdapter 内部 _ensure_client() 懒建 AsyncOpenAI(api_key, base_url)，_serialize_messages 转 API 格式。 |
| **与上下游** | 上游：Builder with_model() 或 with_managers(model_adapter_manager)；Config 可驱动默认模型。下游：Planner/Remediator 用同一 model 做 plan/reflect；Execute/Simple 用 model 做对话与 tool_calls。 |
| **可扩展点** | 实现 IModelAdapter.generate(model_input, options?)；可替换 base_url、extra 或继承覆写 _build_client/_serialize_messages；IModelAdapterManager 支持从配置/环境解析不同后端。 |

## 2.7 其他可挂载

| 类型 | 挂载方式 | 说明 |
|------|----------|------|
| Planner | with_planner() | 实现 IPlanner |
| Validator | add_validators() | 实现 IValidator，可多个 |
| Remediator | with_remediator() | 实现 IRemediator |
| EventLog | with_event_log() | 实现 IEventLog |
| Hooks | add_hooks() | 实现 IHook，**见 2.5 Hook** |
| 模型 | with_model() | 实现 IModelAdapter，**见 2.6 模型** |
| ExecutionControl | with_execution_control() | 实现 IExecutionControl（HITL） |
| Prompt | with_prompt() / with_prompt_id() | 覆盖默认 base.system |

---

# P3：Example 05 如何使用框架搭建 Agent 应用

## 3.1 文件结构（example05 实际）

```
05-dare-coding-agent-enhanced/
├── main.py              # 入口，asyncio.run(cli_main())
├── cli.py               # 交互式 CLI、Builder 组装、事件展示
├── local_mcp_server.py  # 本地 MCP HTTP 服务（四则运算）
├── .dare/mcp/
│   └── local_math.json  # MCP 配置
├── validators/
│   └── file_validator.py  # FileExistsValidator
├── workspace/           # 工作目录
├── demo.py
└── demo_script.txt
```

## 3.2 Builder 组装代码（cli.py _create_builder）

```python
# 1. 创建 Model
model = OpenRouterModelAdapter(model=..., api_key=..., extra={"max_tokens": ...})

# 2. 创建 Knowledge（rawdata 内存）
knowledge = RawDataKnowledge(storage=InMemoryRawDataStorage())

# 3. 本地工具
tools = [ReadFileTool(), WriteFileTool(), SearchCodeTool(), RunCommandTool()]

# 4. 自定义 Validator
validator = FileExistsValidator(workspace=workspace, expected_files=[], verbose=False)

# 5. 事件日志（用于 CLI 展示）
event_log = StreamingEventLog(display.show_event)

# 6. RunContext 工厂（传入 workspace）
run_context_factory = lambda: RunContext(
    metadata={"agent": "dare-coding-agent"},
    config={"workspace_roots": [str(workspace)]},
)

# 7. 组装 Builder
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

# 8. MCP 配置（若 .dare/mcp 存在）
if mcp_dir.exists():
    config = Config(mcp_paths=[str(mcp_dir)], workspace_dir=..., user_dir=...)
    builder = builder.with_config(config)

# 9. Skill（可选）
if initial_skill_path:
    builder = builder.with_skill(initial_skill_path)

# 10. 异步 build（内部会加载 MCP）
agent = await builder.build()
```

## 3.3 执行流程（CLI 视角）

1. **main()** 解析参数，创建 builder，`agent = await builder.build()`
2. **plan 模式**：用户输入任务 → preview_plan() 调用 DefaultPlanner.plan() → 显示计划 → 等待 /approve
3. **execute 模式**：用户输入任务 → `agent.run(Task(description=...))` 直接执行
4. **/approve**：用 pending_task_description 调用 run_task()
5. **StreamingEventLog**：每次 append 时调用 display.show_event()，展示 plan.validated、tool.invoke、tool.result、milestone.success 等

## 3.4 FileExistsValidator 与 Plan 的衔接

- DefaultPlanner 生成 ProposedPlan，steps 中 capability_id 如 `code_creation_evidence`，params 含 `expected_files: ["snake.py"]`
- FileExistsValidator.validate_plan：接受所有 plan，转为 ValidatedPlan
- FileExistsValidator.verify_milestone：从 plan.steps 的 params.expected_files 收集文件列表，检查 workspace 中是否存在；若存在则 VerifyResult(success=True)

---

# P4：Agent 模块设计

## 4.1 接口定义（agent/kernel.py, interfaces.py）

- **IAgent**：`async def run(task: str | Task, deps) -> RunResult`
- **IAgentOrchestration**：`async def execute(task: Task, deps) -> RunResult`

## 4.2 DareAgent 编排流程图

```
run(task)
    │
    ▼
execute(task)  ──► 模式判断
    │
    ├─ [Dare Agent] ──► _run_session_loop(task)
    │       │
    │       ▼
    │   session.start 事件
    │   user_message → stm_add
    │   milestones = task.to_milestones()  // 无则自动生成单个 milestone
    │       │
    │       ▼
    │   FOR each milestone:
    │       │
    │       ▼
    │   _run_milestone_loop(milestone)
    │       │
    │       ├─► budget_check
    │       ├─► _run_plan_loop(milestone)  ──► planner.plan(ctx) → validator.validate_plan()
    │       ├─► _run_execute_loop(validated_plan)
    │       │       │
    │       │       ▼
    │       │   context.assemble() → ModelInput
    │       │   LOOP (max_tool_iterations):
    │       │       model.generate() → response
    │       │       IF no tool_calls: 添加 assistant_message → STM，返回
    │       │       FOR each tool_call:
    │       │           IF _is_plan_tool_call: return encountered_plan_tool
    │       │           _run_tool_loop(ToolLoopRequest) → tool_gateway.invoke()
    │       │           tool_result → tool_msg → stm_add
    │       │       reassemble → 下一轮
    │       │
    │       ├─► IF encountered_plan_tool: add_reflection, continue (重试 milestone)
    │       ├─► _verify_milestone(execute_result, validated_plan)  // validator.verify_milestone
    │       ├─► IF verify_result.success: return MilestoneResult(success=True)
    │       └─► ELSE: remediator.remediate() → add_reflection, 下一轮 attempt
    │
    │   session.complete 事件
    │   return RunResult(success, output, errors)
    │
    ├─ [ReAct] ──► _run_react_loop(task)
    │       user_message → stm_add
    │       _run_execute_loop(None)  // 无 plan
    │       return RunResult(...)
    │
    └─ [Chat] ──► _run_chat_loop(task)
            user_message → stm_add
            context.assemble() → model.generate()  // tools=[]
            assistant_message → stm_add
            return RunResult(output={"content": ...})
```

### 4.2.1 DareAgent 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | `Task(description, task_id, milestones?)`；可选 deps。 |
| **输出** | `RunResult(success, output, errors, metadata)`。 |
| **模式选择** | `is_full_five_layer_mode`（有 planner 或 task.milestones）→ Session 循环；`is_react_mode`（无 planner 有 tool_gateway）→ ReAct 循环；否则 `is_simple_mode` → 单次 generate。 |
| **Session 循环** | 初始化 SessionState、user_message→STM、task.to_milestones() 得到里程碑列表，按序执行 _run_milestone_loop；每里程碑前 budget_check、可选 execution_control.poll_or_raise。 |
| **Milestone 循环** | 最多 max_milestone_attempts 次：Plan 循环 → Execute 循环 → 若遇 plan_tool 则 add_reflection 并 continue → _verify_milestone → 成功则返回 MilestoneResult；否则 remediator.remediate → add_reflection，下一轮。 |
| **Plan 循环** | 无 planner 返回 None；有则最多 max_plan_attempts 次：context.assemble() → planner.plan(ctx) → validator.validate_plan(proposed, ctx)；通过则返回 ValidatedPlan，否则记录 attempt 并重试。 |
| **Execute 循环** | context.assemble() → ModelInput(messages, tools) → 循环最多 max_tool_iterations：model.generate() → 无 tool_calls 则 assistant_message→STM 并返回；有则逐条 _run_tool_loop，结果 tool_msg→STM，再 reassemble 进入下一轮。若遇 plan_tool 则返回 encountered_plan_tool。 |
| **Tool 循环** | budget_use("tool_calls",1)、BEFORE_TOOL hook、event_log.append("tool.invoke") → tool_gateway.invoke(capability_id, params, envelope) → event_log.append("tool.result")、AFTER_TOOL hook；若 result.evidence 则 milestone_state.add_evidence。 |
| **Verify** | 无 validator 返回 VerifyResult(success=True)；有则 execute_result 转为 RunResult，调用 validator.verify_milestone(run_result, ctx, plan=validated_plan)。 |
| **与上下游** | 上游：Builder 注入 model/context/planner/validator/remediator/tool_gateway/event_log/hooks。下游：Context（STM、assemble）、Model（generate）、Planner/Validator/Remediator、IToolGateway（invoke）、IEventLog（append）、IHook（invoke）。 |
| **可扩展点** | 实现 IAgentOrchestration 可替换编排策略；HookPhase 各阶段挂载观测/审批；ExecutionControl 实现 HITL。 |

## 4.3 Builder 工作逻辑图与解析顺序（builder.py）

### 4.3.1 Builder 工作逻辑图

```
build() [async]
    │
    ├─► IF config.mcp_paths: load_mcp_toolkit() → MCPToolkit.initialize()，得到 _mcp_toolkit
    │
    ├─► _resolved_tools()
    │       explicit = self._tools
    │       IF _mcp_toolkit: mcp_tools = list_tools()，按 config.allowmcps 过滤，与 explicit 去重合并
    │       IF manager: manager_tools = manager.load_tools(config)，与 explicit/mcp 去重，按 config 过滤
    │       return [*explicit, *mcp_tools, *manager_tools]
    │
    ├─► manager = _ensure_tool_manager(tools)   // 无则 new ToolManager(context_factory)
    ├─► _register_tools_with_manager(manager, tools)
    │       FOR each tool: manager.register_tool(tool)
    │       IF _resolved_knowledge(): manager.register_tool(KnowledgeGetTool), KnowledgeAddTool
    │
    ├─► tool_gateway = _ensure_tool_gateway(tools)   // 即 manager
    ├─► tool_provider = _ensure_tool_provider(manager, tools)   // 可能为 _ConfiguredToolProvider(allowtools 等)
    │
    ├─► _resolve_sys_prompt(model)
    │       prompt_id = override | config.default_prompt_id | "base.system"
    │       store = _resolve_prompt_store() → LayeredPromptStore
    │       return store.get(prompt_id, model=model_name)
    │
    ├─► context = Context(...) 或 _apply_context_overrides(self._context)
    │       context._tool_provider = tool_provider
    │       context._sys_prompt = sys_prompt
    ├─► _load_initial_skill_and_mount(context)
    │       path = initial_skill_path | config.initial_skill_path
    │       FileSystemSkillLoader(path).load() → skills; IF skills: context.set_skill(skills[0])
    │
    └─► [DareAgentBuilder] planner/validator/remediator 解析
            validator = CompositeValidator(validators) if len(validators)>1
            构造 DareAgent(model, context, tools, tool_gateway, planner, validator, remediator, event_log, hooks, ...)
```

### 4.4 Builder 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | 链式配置：with_model、add_tools、with_knowledge、with_planner、add_validators、with_remediator、with_event_log、with_config 等。 |
| **输出** | IAgent 实例（DareAgent / ReactAgent / SimpleChatAgent）。 |
| **工具解析顺序** | ① build() 若 config.mcp_paths 非空 → load_mcp_toolkit()；② _resolved_tools() = explicit + mcp_toolkit.list_tools()（按 allowmcps 过滤）+ manager.load_tools()；③ _register_tools_with_manager() 注册所有 tool，若有 knowledge 则注册 knowledge_get、knowledge_add；④ _ensure_tool_provider() 可能返回 _ConfiguredToolProvider（按 config.allowtools 等过滤）。 |
| **上下文与 Prompt** | _resolve_sys_prompt(model) 使用 prompt_id override / config.default_prompt_id / "base.system"，从 LayeredPromptStore 取 Prompt；context._sys_prompt、context._tool_provider 注入。 |
| **Skill 挂载** | _load_initial_skill_and_mount(context)：从 initial_skill_path 或 config.initial_skill_path 用 FileSystemSkillLoader 加载，取第一个 skill 调用 context.set_skill(skills[0])。 |
| **与上下游** | 上游：Config、IModelAdapter、ITool、IKnowledge、IPlanner、IValidator、IRemediator、IEventLog、IHook。下游：Context、ToolManager、DareAgent/ReactAgent/SimpleChatAgent。 |
| **可扩展点** | 继承 _BaseAgentBuilder 实现 _build_impl()；with_managers() 注入各 Manager 实现 Config 驱动解析；with_prompt/store 覆盖默认 Prompt。 |

## 4.5 ReactAgent 编排流程图

```
_execute(task)
    │
    ├─► user_message = Message(role="user", content=task)
    ├─► context.stm_add(user_message)
    ├─► gateway = context._tool_provider; has_invoke = gateway 有 invoke 方法
    │
    └─► FOR round in range(max_tool_rounds):  // 默认 10 轮
            │
            ├─► assembled = context.assemble()
            │   messages = [sys_prompt_message, *assembled.messages] if sys_prompt else assembled.messages
            ├─► model_input = ModelInput(messages=messages, tools=assembled.tools, metadata=assembled.metadata)
            ├─► response = await model.generate(model_input)
            ├─► IF response.usage: budget_use("tokens", total_tokens); budget_check()
            │
            ├─► IF not response.tool_calls:
            │       assistant_message = Message(role="assistant", content=response.content)
            │       context.stm_add(assistant_message)
            │       return response.content  // 完成，返回最终回复
            │
            ├─► IF not has_invoke:
            │       assistant_message = Message(role="assistant", content="(Tool calls returned but no tool gateway...)")
            │       context.stm_add(assistant_message)
            │       return response.content or "(Tool calls not executed.)"
            │
            ├─► assistant_msg = Message(role="assistant", content=response.content, metadata={"tool_calls": tool_calls})
            ├─► context.stm_add(assistant_msg)
            │
            └─► FOR each tool_call in response.tool_calls:
                    name = tool_call.get("name"); tool_call_id = tool_call.get("id"); args = tool_call.get("arguments")
                    IF args is str: args = json.loads(args) or {}
                    params = args if dict else {}
                    TRY:
                        result = await gateway.invoke(name, params, envelope=Envelope())
                    EXCEPT Exception as exc:
                        result = mock_result(success=False, error=str(exc))
                    success, output, error = getattr(result, "success", False), getattr(result, "output", {}), getattr(result, "error", "")
                    tool_content = json.dumps({"success": success, "output": output, "error": error} if not success else {"success": True, "output": output})
                    tool_msg = Message(role="tool", name=tool_call_id or name, content=tool_content)
                    context.stm_add(tool_msg)
                // 下一轮 reassemble → model.generate
    
    return "(Reached max tool rounds without final reply.)"
```

### 4.5.1 ReactAgent 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | task: str；构造时需 model: IModelAdapter、context?: Context、tools?: IToolProvider、max_tool_rounds=10。 |
| **输出** | str：最终 response.content 或 "(Reached max tool rounds...)" 或 "(Tool calls not executed.)"。 |
| **关键步骤** | ① user_message→STM；② 循环最多 max_tool_rounds 次：assemble → ModelInput → model.generate；③ 无 tool_calls 则 assistant_message→STM 并返回；④ 有 tool_calls 则 assistant_msg（含 metadata）→STM，逐条 gateway.invoke(name, params, envelope) → tool_msg→STM；⑤ 下一轮 reassemble。 |
| **与 DareAgent 差异** | 无 Session/Milestone/Plan/Verify 循环；无 planner/validator/remediator；无 event_log/hooks；直接 Execute→Tool 循环（ReAct 模式）；envelope 为空 Envelope()，无 allowed_capability_ids 等限制。 |
| **与上下游** | 上游：ReactAgentBuilder 注入 model、context、tools（作为 _tool_provider）；无需 planner/validator。下游：Context（STM、assemble）、Model（generate）、IToolProvider（invoke，通常为 ToolManager）。 |
| **可扩展点** | 继承 ReactAgent 覆写 _execute；调整 max_tool_rounds；替换 gateway（IToolProvider 或 IToolGateway）；可选注入 knowledge 供 context 使用。 |

---

# P5：Context 模块设计

## 5.1 接口（context/kernel.py）

- **IRetrievalContext**：`get(query, **kwargs) -> list[Message]`
- **IContext**：id, short_term_memory, budget, long_term_memory, knowledge, toollist, config；stm_add/stm_get/stm_clear；budget_use/budget_check；listing_tools；assemble；compress

## 5.2 assemble() 工作逻辑图

```
assemble(**options)
    │
    ├─► messages = stm_get()
    │       short_term_memory.get()  // IRetrievalContext，InMemorySTM 返回 list(_messages)
    │
    ├─► tools = listing_tools()
    │       IF _tool_provider:
    │           list_tool_defs = getattr(provider, "list_tool_defs", None)
    │           IF callable: toollist = list_tool_defs()
    │           ELSE: toollist = provider.list_tools() 转 dict 兼容
    │       return toollist or []
    │
    ├─► sys_prompt = _sys_prompt
    ├─► IF _current_skill and sys_prompt:
    │       sys_prompt = enrich_prompt_with_skill(sys_prompt, skill)
    │       // 追加 "## Skill: {name}\n\n{content}" 和 "## Available Scripts (call via run_command)\n\n- skill_id/name: `cmd [args]`"
    │
    └─► return AssembledContext(messages, sys_prompt, tools, metadata={"context_id": id})
```

### 5.2.1 Context 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | assemble() 无必选参数；stm_add(message)、budget_use(resource, amount)、set_skill(skill) 等由 Agent 在运行中调用。 |
| **输出** | AssembledContext(messages, sys_prompt, tools, metadata)；listing_tools() 返回 list[dict] 供 ModelInput.tools。 |
| **关键步骤** | stm_get→listing_tools→取 _sys_prompt→若有 skill 则 enrich_prompt_with_skill→返回 AssembledContext。compress() 委托 short_term_memory.compress(max_messages) 保留最近 N 条。 |
| **与上下游** | 上游：Agent 注入 _tool_provider、_sys_prompt；Builder 或 set_skill 注入 _current_skill。下游：assemble() 产出供 ModelInput；STM 供 Planner/Execute 读写消息。 |
| **可扩展点** | 实现 IContext 并覆写 assemble() 可自定义组装逻辑；short_term_memory 可替换为其他 IRetrievalContext 实现。 |

## 5.3 Budget（context/types.py）工作逻辑与要点

| 项目 | 说明 |
|------|------|
| **字段** | max_tokens, max_cost, max_time_seconds, max_tool_calls；used_tokens, used_cost, used_time_seconds, used_tool_calls。 |
| **budget_use(resource, amount)** | resource 为 "tokens"|"cost"|"time_seconds"|"tool_calls"，累加对应 used_*。 |
| **budget_check()** | 任一项 used_* > max_* 则 raise RuntimeError（Token/Cost/Tool call/Time budget exceeded）。 |
| **budget_remaining(resource)** | 返回 max - used，未设 max 则 inf。 |

---

# P6：Plan 模块设计

## 6.1 类型（plan/types.py）

- Task：description, task_id, milestones, metadata
- Milestone：milestone_id, description, user_input, success_criteria
- ProposedPlan：plan_description, steps (ProposedStep)
- ValidatedPlan：plan_description, steps (ValidatedStep), success, errors
- ProposedStep / ValidatedStep：step_id, capability_id, params, description；ValidatedStep 多了 risk_level, envelope
- VerifyResult：success, errors, metadata
- RunResult：success, output, errors, metadata
- ToolLoopRequest：capability_id, params, envelope
- Envelope：allowed_capability_ids, budget, done_predicate, risk_level

## 6.2 DefaultPlanner 工作逻辑图

```
plan(ctx)
    │
    ├─► messages = ctx.stm_get()
    │   task_description = messages[-1].content if messages else "Unknown task"
    │
    ├─► user_prompt = "Task: {task_description}\nPlease analyze and generate Implementation Plan.\nOutput ONLY valid JSON..."
    ├─► model_input = ModelInput(messages=[Message(system, _system_prompt), Message(user, user_prompt)])
    ├─► response = await model.generate(model_input)
    ├─► plan_data = _parse_response(response.content)
    │       content 去首尾、去 ``` 代码块 → json.loads
    │   IF 解析异常: return _fallback_plan(task_description)
    │
    ├─► steps = [ProposedStep(step_id, capability_id, params, description) for step in plan_data.get("steps", [])]
    └─► return ProposedPlan(plan_description=plan_data.get("plan_description", task_description), steps=steps)
```

**Evidence 类型**（DEFAULT_PLAN_SYSTEM_PROMPT 中定义）：file_evidence, search_evidence, summary_evidence, code_creation_evidence, functionality_evidence, integration_evidence 等。

### 6.2.1 DefaultPlanner 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | ctx: IContext，任务描述来自 ctx.stm_get() 最后一条消息的 content。 |
| **输出** | ProposedPlan(plan_description, steps: list[ProposedStep])。 |
| **关键步骤** | 从 STM 取任务描述 → 拼 user_prompt → ModelInput(仅 system+user，无 tools) → model.generate → _parse_response 解析 JSON；异常时 _fallback_plan 按任务关键词（写/创建/实现 vs 其他）返回预设 evidence 步骤。 |
| **与上下游** | 上游：DareAgent 在 _run_plan_loop 中调用；ctx 由 Agent 注入。下游：产出 ProposedPlan 交给 Validator.validate_plan。 |
| **可扩展点** | 实现 IPlanner.plan(ctx)；可替换 _system_prompt 或继承 DefaultPlanner 覆写 plan/_parse_response/_fallback_plan。 |

## 6.3 IValidator 工作逻辑图与要点（CompositeValidator）

```
validate_plan(plan, ctx)
    current = plan
    FOR each validator in _validators:
        current = await validator.validate_plan(current, ctx)
        IF not getattr(current, "success", True): return current
    return current

verify_milestone(result, ctx, *, plan=None)
    last = None
    FOR each validator in _validators:
        last = await validator.verify_milestone(result, ctx, plan=plan)
        IF not getattr(last, "success", True): return last
    return last
```

### 6.3.1 IValidator 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | validate_plan(plan, ctx)：ProposedPlan + IContext。verify_milestone(result, ctx, plan)：RunResult + IContext + ValidatedPlan（可选，用于按 step 标准校验，如 expected_files）。 |
| **输出** | validate_plan 返回 ValidatedPlan（含 success, errors）；verify_milestone 返回 VerifyResult(success, errors, metadata)。 |
| **关键步骤** | CompositeValidator 顺序执行多个 IValidator；任一 success=False 即提前返回。单 Validator（如 FileExistsValidator）在 verify_milestone 中从 plan.steps 的 params.expected_files 收集文件列表，检查 workspace 中是否存在。 |
| **与上下游** | 上游：DareAgent _run_plan_loop 调用 validate_plan；_verify_milestone 调用 verify_milestone。下游：ValidatedPlan 供 Execute 使用；VerifyResult 供 Remediator 与 milestone 重试判断。 |
| **可扩展点** | 实现 IValidator.validate_plan / verify_milestone；可多个通过 Builder.add_validators 注入，由 CompositeValidator 组合。 |

## 6.4 DefaultRemediator 工作逻辑图与要点

```
remediate(verify_result, ctx)
    errors = verify_result.errors or ["Unknown failure"]
    messages = ctx.stm_get(); recent = messages[-3:] if len(messages)>=3 else messages
    user_prompt = "## Verification Failed\n**Errors**: ...\n**Metadata**: ...\n**Recent Context**: ..."
    model_input = ModelInput([Message(system, DEFAULT_REFLECT_SYSTEM_PROMPT), Message(user, user_prompt)])
    response = await model.generate(model_input)
    IF 异常: return _fallback_reflection(errors)
    return response.content.strip()  // 供 milestone_state.add_reflection
```

### 6.4.1 DefaultRemediator 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | verify_result: VerifyResult（含 errors, metadata）；ctx: IContext。 |
| **输出** | str：结构化反思文本（Failure Analysis / Meta-Reflection / Recommended Adjustments / Summary for Next Attempt）。 |
| **关键步骤** | 取 verify_result.errors 与 ctx.stm_get() 最近 3 条拼 user_prompt → ModelInput(仅 system+user) → model.generate → 返回 content；异常时 _fallback_reflection 返回简短模板。 |
| **与上下游** | 上游：DareAgent 在 milestone 验证失败后调用 remediate(verify_result, ctx)；反思文本写入 milestone_state.add_reflection，下一轮 Plan 可参考。下游：无直接下游，反思用于下一轮 plan 的上下文。 |
| **可扩展点** | 实现 IRemediator.remediate(verify_result, ctx)；可替换 system_prompt 或继承覆写 remediate/_fallback_reflection。 |

---

# P7：Tool 模块设计

## 7.1 接口（tool/kernel.py, interfaces.py）

- **IToolGateway**：list_capabilities(), invoke(capability_id, params, envelope)
- **IToolManager**：extends IToolGateway；register_tool, load_tools, list_tool_defs, get_capability, health_check
- **ITool**：name, description, input_schema, output_schema, risk_level, tool_type, requires_approval, timeout_seconds, is_work_unit, capability_kind；execute(input, context) -> ToolResult
- **IToolProvider**：list_tools() -> list[ITool]
- **RunContext**：deps, run_id, task_id, milestone_id, metadata, config

## 7.2 ToolManager 工作逻辑图

```
register_tool(tool, namespace?, version?)
    IF id(tool) in _tool_index_by_object: return existing entry.descriptor
    capability_id = tool.name
    IF capability_id in _registry: raise ValueError("Tool name already registered")
    descriptor = _descriptor_from_tool(tool, capability_id)
    _registry[capability_id] = _registry_entry(descriptor, enabled=True, source=_TOOL_SOURCE, tool=tool)
    _tool_index_by_object[id(tool)] = capability_id
    return descriptor

register_provider(provider)
    _providers.append(provider); _sync_provider_tools(provider, provider.list_tools())
    // 对每个 tool 调用 _register_provider_tool(provider, tool)，source=provider

invoke(capability_id, params, envelope)
    IF envelope.allowed_capability_ids and capability_id not in allowed: raise PermissionError
    entry = _registry.get(capability_id)
    IF entry is None or not entry.enabled or entry.tool is None: raise KeyError
    context = _context_factory()
    return await entry.tool.execute(params, context)
```

### 7.2.1 ToolManager 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | register_tool(tool)：ITool。invoke(capability_id, params, envelope)：由 Agent _run_tool_loop 传入，envelope 含 allowed_capability_ids、done_predicate 等。 |
| **输出** | register_tool 返回 CapabilityDescriptor；invoke 返回 ToolResult(success, output, error, evidence)。 |
| **关键步骤** | 注册：tool.name 作为 capability_id，_descriptor_from_tool 生成 descriptor，存 _registry。Provider 注册时 _sync_provider_tools 遍历 list_tools() 逐条 _register_provider_tool。调用：envelope 权限检查 → 取 entry → context_factory() 得 RunContext → entry.tool.execute(params, context)。 |
| **与上下游** | 上游：Builder _register_tools_with_manager 注册显式工具 + KnowledgeGetTool/KnowledgeAddTool；load_mcp_toolkit 后 MCPToolkit 作为 provider 或工具列表合并后注册。下游：Native Tool 直接 execute；MCPTool 委托 client.call_tool。 |
| **可扩展点** | 实现 IToolManager 或注册 IToolProvider；ITool 实现 name/input_schema/execute 等；context_factory 由 Builder with_run_context_factory 注入。 |

## 7.3 MCPToolkit 工作逻辑图

```
initialize()
    _tools.clear()
    FOR each client in _clients:
        await client.connect()
        FOR each tool_def in await client.list_tools():
            tool_name = tool_def.name or ""
            IF not tool_name: continue
            full_name = f"{client.name}:{tool_name}"
            _tools[full_name] = MCPTool(client=client, tool_def=tool_def, tool_name=tool_name, full_name=full_name)

list_tools()
    return list(_tools.values())  // MCPTool 实现 ITool，name 为 full_name（如 local_math:add）
```

### 7.3.1 MCPToolkit / MCPTool 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | MCPToolkit(clients: Sequence[IMCPClient])；initialize() 由 Builder.build() 内 load_mcp_toolkit 后调用。MCPTool.execute(input, context) 由 ToolManager.invoke → entry.tool.execute 调用。 |
| **输出** | list_tools() 返回 list[ITool]（MCPTool 列表）；MCPTool.execute 返回 await client.call_tool(tool_name, input, context)。 |
| **关键步骤** | initialize：对每个 client connect → list_tools() → 为每个 tool_def 建 MCPTool(client, tool_def, tool_name, full_name)。MCPTool 属性从 tool_def 取（description, input_schema, risk_level 等）；execute 委托 client.call_tool。 |
| **与上下游** | 上游：load_mcp_configs → create_mcp_clients → MCPToolkit(clients)；Builder _resolved_tools 合并 mcp_toolkit.list_tools()。下游：ToolManager 注册后 invoke 时 entry.tool.execute 即 MCPTool.execute → MCP client.call_tool。 |
| **可扩展点** | 新增 transport（如 gRPC）或新 MCP 客户端实现 IMCPClient；MCPTool 通过 tool_def 扩展 metadata。 |

## 7.4 工具调用链路工作逻辑图（DareAgent → ToolManager）

```
_run_tool_loop(ToolLoopRequest)
    │
    ├─► budget_check, budget_use("tool_calls", 1)
    ├─► event_log.append("tool.invoke", ...)
    ├─► result = tool_gateway.invoke(capability_id, params, envelope)
    │       │
    │       └─► ToolManager: context = _context_factory()
    │           return await entry.tool.execute(params, context)
    │               │
    │               ├─ Native Tool: 直接执行
    │               └─ MCPTool: client.call_tool(tool_name, input, context)
    │
    ├─► event_log.append("tool.result", ...)
    ├─► IF result.evidence: milestone_state.add_evidence(...)
    └─► return {success, output, error, result}
```

### 7.4.1 工具调用链路要点说明

| 项目 | 说明 |
|------|------|
| **输入** | _run_tool_loop(ToolLoopRequest(capability_id, params), tool_name, tool_call_id, descriptor)。 |
| **输出** | dict：success, output, error, result（及可选 evidence 已写入 milestone_state）。 |
| **关键步骤** | budget_check → budget_use("tool_calls",1) → BEFORE_TOOL hook → event_log.append("tool.invoke") → tool_gateway.invoke(capability_id, params, envelope) → event_log.append("tool.result") → 若 result.evidence 则 milestone_state.add_evidence → AFTER_TOOL hook；envelope.allowed_capability_ids 在 ToolManager.invoke 内校验。 |
| **与上下游** | 上游：Execute 循环中 model 返回 tool_calls，逐条构造 ToolLoopRequest 调用 _run_tool_loop。下游：tool_gateway 通常为 ToolManager，invoke 内执行 Native 或 MCPTool.execute。 |
| **可扩展点** | ExecutionControl 在 tool 前 poll_or_raise 实现 HITL；HookPhase.BEFORE_TOOL/AFTER_TOOL 挂载审批/日志。 |

---

# P8：Knowledge 模块设计

## 8.1 接口（knowledge/kernel.py, knowledge_tools.py）

- **IKnowledge**：get(query, **kwargs) -> list[Message]；add(content, **kwargs)
- **KnowledgeGetTool**：name="knowledge_get"，execute 调用 knowledge.get(query, top_k)
- **KnowledgeAddTool**：name="knowledge_add"，execute 调用 knowledge.add(content, metadata)

## 8.2 RawDataKnowledge 工作逻辑图

```
add(content, **kwargs)
    metadata = kwargs.get("metadata") or {}
    _storage.add(content, metadata=metadata)
    // InMemoryRawDataStorage: 存 RawRecord(id, content, metadata)

get(query="", **kwargs)
    top_k = kwargs.get("top_k", 5)
    records = _storage.search(query=query, top_k=top_k)  // substring 匹配 content
    return [Message(role="assistant", content=r.content, name=r.metadata.get("source") or r.id, metadata={**r.metadata, "document_id": r.id}) for r in records]
```

### 8.2.1 RawDataKnowledge 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | add(content, metadata?)；get(query, top_k?)；由 KnowledgeGetTool/KnowledgeAddTool 在 execute 时调用。 |
| **输出** | add 无返回值；get 返回 list[Message]（role=assistant，content=记录内容）。 |
| **关键步骤** | add 委托 storage.add；get 委托 storage.search（substring 匹配），将 RawRecord 转为 Message。storage 可选 InMemoryRawDataStorage 或 SQLiteRawDataStorage。 |
| **与上下游** | 上游：Builder with_knowledge(knowledge) 或 create_knowledge(config) 注入；ToolManager 注册 KnowledgeGetTool(knowledge)、KnowledgeAddTool(knowledge)。下游：Agent 通过 knowledge_get/knowledge_add 工具调用 get/add。 |
| **可扩展点** | 实现 IKnowledge 或替换 IRawDataStore（in_memory | sqlite）。 |

## 8.3 VectorKnowledge 工作逻辑图与要点

```
add(content, **kwargs)
    metadata = kwargs.get("metadata") or {}; auto_embed = kwargs.get("auto_embed", True)
    doc = Document(content=content, metadata=metadata)
    add_document(doc, auto_embed=auto_embed)  // 若 auto_embed 则 embed 后 vector_store.add

get(query, **kwargs)
    top_k, min_similarity, auto_embed = kwargs.get("top_k",5), kwargs.get("min_similarity"), kwargs.get("auto_embed", True)
    IF auto_embed: query_vector = embedding_adapter.embed(query).vector
    ELSE: query_vector = query  // 假定 query 已是向量
    search_results = vector_store.search(query_embedding=query_vector, top_k=top_k, min_similarity=min_similarity)
    return [doc.to_message(); message.metadata["similarity"]=similarity for doc, similarity in search_results]
```

| 项目 | 说明 |
|------|------|
| **输入** | add(content, metadata?, auto_embed?)；get(query, top_k?, min_similarity?, auto_embed?)；需 IEmbeddingAdapter。 |
| **输出** | get 返回 list[Message]，metadata 含 similarity。 |
| **关键步骤** | add 包成 Document，可选 embed 后写入 vector_store。get 对 query 做 embed（或直接用向量）→ vector_store.search → 转 Message 并带 similarity。storage 可选 InMemoryVectorStore、SQLiteVectorStore、ChromaDBVectorStore。 |
| **与上下游** | 上游：create_knowledge(config type="vector", embedding_adapter) 或显式 VectorKnowledge(embedding_adapter, vector_store)。下游：同 RawDataKnowledge，通过 knowledge_get/knowledge_add 调用。 |
| **可扩展点** | 实现 IKnowledge 或替换 IVectorStore、IEmbeddingAdapter。 |

## 8.4 create_knowledge 工作逻辑图与要点（factory.py）

```
create_knowledge(config, embedding_adapter)
    IF config 为空: return None
    cfg = KnowledgeConfig.from_dict(config) if dict else config
    IF cfg.type == "rawdata":
        opts = cfg.options
        store = SQLiteRawDataStorage(Path(opts.get("path") or ".dare/rawdata.db")) if cfg.storage=="sqlite" else InMemoryRawDataStorage()
        return RawDataKnowledge(storage=store)
    IF cfg.type == "vector":
        IF embedding_adapter is None: return None
        opts = cfg.options
        IF cfg.storage == "chromadb": store = ChromaDBVectorStore(collection_name, path, host, port)
        ELIF cfg.storage == "sqlite": store = SQLiteVectorStore(Path(opts.get("path") or ".dare/vectors.db"))
        ELSE: store = InMemoryVectorStore()
        return VectorKnowledge(embedding_adapter=embedding_adapter, vector_store=store)
    return None
```

### 8.4.1 create_knowledge 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | config: dict 或 KnowledgeConfig（type, storage, options）；embedding_adapter 仅在 type="vector" 时必需。 |
| **输出** | IKnowledge 实例或 None（config 空或 vector 无 embedding_adapter）。 |
| **关键步骤** | type "rawdata" → 按 storage 选 InMemoryRawDataStorage/SQLiteRawDataStorage → RawDataKnowledge。type "vector" → 需 embedding_adapter，按 storage 选 ChromaDB/SQLite/InMemory VectorStore → VectorKnowledge。 |
| **与上下游** | 上游：Builder with_knowledge() 显式注入或 Config.knowledge + with_embedding_adapter 在 _resolved_knowledge() 中调用 create_knowledge。下游：Context.knowledge、ToolManager 注册 knowledge_get/knowledge_add。 |
| **可扩展点** | 扩展 KnowledgeConfig 与 factory 分支支持新 type/storage。 |

---

# P9：Model 模块设计

## 9.1 接口（model/kernel.py）

- **IModelAdapter**：generate(model_input) -> ModelResponse
- **ModelInput**：messages, tools, metadata
- **ModelResponse**：content, tool_calls, usage

## 9.2 OpenRouterModelAdapter 工作逻辑图

```
generate(model_input, options?)
    client = _ensure_client()  // 懒建 AsyncOpenAI(api_key, base_url=OpenRouter)
    messages = _serialize_messages(model_input.messages)  // Message → OpenAI 格式
    api_params = {model, messages}
    IF model_input.tools: api_params["tools"] = model_input.tools
    IF _extra: api_params.update(_extra)
    IF options: temperature, max_tokens, top_p, stop 等合并进 api_params
    response = await client.chat.completions.create(**api_params)
    message = response.choices[0].message
    content = message.content or ""
    tool_calls = _extract_tool_calls(message)  // id, name/capability_id, arguments
    usage = {prompt_tokens, completion_tokens, total_tokens} if response.usage else None
    return ModelResponse(content=content, tool_calls=tool_calls, usage=usage, metadata={model, finish_reason})
```

### 9.2.1 OpenRouterModelAdapter 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | ModelInput(messages, tools?, metadata?)；options?: GenerateOptions(temperature, max_tokens, top_p, stop)。 |
| **输出** | ModelResponse(content, tool_calls, usage, metadata)。 |
| **关键步骤** | _ensure_client 懒建 AsyncOpenAI(api_key, base_url)；_serialize_messages 将 Message 转为 API 格式；若有 tools 则传入 api_params；create 后取 message.content、_extract_tool_calls(message)、usage。 |
| **与上下游** | 上游：DareAgent/ReactAgent/SimpleChatAgent 在 Plan/Execute/Simple 循环中 context.assemble() → ModelInput(messages, tools) → model.generate(model_input)。下游：response.content 与 response.tool_calls 供 Agent 写 STM 与 _run_tool_loop。 |
| **可扩展点** | 实现 IModelAdapter.generate(model_input, options?)；可替换 base_url、extra 或继承覆写 _build_client/_serialize_messages。 |

## 9.3 Prompt 解析工作逻辑图与要点（builder._resolve_sys_prompt）

```
_resolve_sys_prompt(model)
    IF _prompt_override is not None: return _prompt_override
    model_name = getattr(model, "name", None); IF not model_name: raise ValueError
    store = _resolve_prompt_store()  // _prompt_store or create_default_prompt_store(config)
    prompt_id = _prompt_id_override or config.default_prompt_id or "base.system"
    return store.get(prompt_id, model=model_name)
```

| 项目 | 说明 |
|------|------|
| **输入** | Builder 链式 with_prompt(prompt) / with_prompt_id(id) / with_prompt_store(store)；model 用于 store.get(..., model=model_name)。 |
| **输出** | Prompt(prompt_id, role, content, supported_models, order)，写入 context._sys_prompt。 |
| **关键步骤** | 显式 with_prompt 优先；否则 prompt_id = override | config.default_prompt_id | "base.system"，从 LayeredPromptStore 取 Prompt。 |
| **与上下游** | 上游：Builder with_prompt/store/prompt_id、Config.default_prompt_id。下游：context._sys_prompt 在 assemble() 中作为 system 内容拼入 ModelInput。 |
| **可扩展点** | 实现 IPromptStore；LayeredPromptStore 可叠加 BuiltinPromptLoader、FilesystemPromptLoader 等。 |

---

# P10：Memory 模块设计

## 10.1 InMemorySTM 工作逻辑图

```
add(message)
    _messages.append(message)

get(query="", **kwargs)
    return list(_messages)  // IRetrievalContext.get；query 忽略，返回全部

clear()
    _messages.clear()

compress(max_messages=None, **kwargs)
    IF max_messages is None or len(_messages) <= max_messages: return 0
    removed_count = len(_messages) - max_messages
    _messages = _messages[-max_messages:]  // 保留最近 N 条
    return removed_count
```

### 10.1.1 InMemorySTM 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | add(message: Message)；get(query, **kwargs)（query 未用）；compress(max_messages?, **kwargs)。 |
| **输出** | get 返回 list[Message]；compress 返回移除条数。 |
| **关键步骤** | 内部 list 存 Message；get 返回副本；compress 仅保留最近 max_messages 条。Context 默认 __post_init__ 时若 short_term_memory 为 None 则创建 InMemorySTM()。 |
| **与上下游** | 上游：Context 持有 short_term_memory；Agent 通过 context.stm_add/stm_get/stm_clear/compress 读写。下游：assemble() 时 stm_get() 取 messages 拼入 ModelInput。 |
| **可扩展点** | 实现 IShortTermMemory（继承 IRetrievalContext，add/clear/compress）；可替换为持久化或带检索的 STM。 |

---

# P11：Event、Hook、Config 模块

## 11.1 IEventLog 工作逻辑与要点

| 项目 | 说明 |
|------|------|
| **接口** | append(event_type, payload) -> event_id；query(filter?, limit=100) -> Sequence[Event]；replay(from_event_id) -> RuntimeSnapshot；verify_chain() -> bool。 |
| **输入/输出** | Agent/控制面调用 append 写入审计事件（如 session.start、plan.validated、tool.invoke、tool.result、milestone.success）；query/replay 供审计与可重放；verify_chain 校验事件链完整性。 |
| **关键步骤** | 实现类（如 StreamingEventLog）在 append 时除持久化外可回调 display.show_event(payload)；DareAgent 在 _log_event 中调用 event_log.append(type, payload)。 |
| **与上下游** | 上游：DareAgent 在各阶段 _log_event("session.start", ...)、("tool.invoke", ...) 等。下游：CLI/观测层通过 query 或 replay 展示/重放。 |
| **可扩展点** | 实现 IEventLog；可对接 WORM 存储、哈希链、流式展示等。 |

## 11.2 IHook 工作逻辑图与要点

```
HookExtensionPoint.emit(phase, payload)
    FOR each callback in _callbacks.get(phase, []): callback(payload)  // 同步，异常仅 log
    FOR each hook in _hooks: await hook.invoke(phase, payload=payload)  // 异步，异常仅 log
```

**HookPhase**（hook/types.py）：BEFORE_RUN, AFTER_RUN, BEFORE_SESSION, AFTER_SESSION, BEFORE_MILESTONE, AFTER_MILESTONE, BEFORE_PLAN, AFTER_PLAN, BEFORE_EXECUTE, AFTER_EXECUTE, BEFORE_CONTEXT_ASSEMBLE, AFTER_CONTEXT_ASSEMBLE, BEFORE_MODEL, AFTER_MODEL, BEFORE_TOOL, AFTER_TOOL, BEFORE_VERIFY, AFTER_VERIFY。

| 项目 | 说明 |
|------|------|
| **输入** | invoke(phase: HookPhase, *args, **kwargs)；payload 由 DareAgent 在各阶段传入（如 task_id, iteration, model_usage, budget_stats）。 |
| **输出** | best-effort，无返回值要求；失败不中断主流程，仅打 log。 |
| **关键步骤** | DareAgent 持有 HookExtensionPoint(self._hooks)，在 execute/session/milestone/plan/execute/model/tool/verify 前后调用 await _emit_hook(phase, payload)。HookExtensionPoint 先执行 register_hook 的 callbacks，再执行 IHook 的 invoke。 |
| **与上下游** | 上游：Builder add_hooks(*hooks) 或 hook_manager 解析；DareAgent 构造时传入 hooks。下游：ObservabilityHook 等可向 ITelemetryProvider 上报；自定义 Hook 可做审批、日志、指标。 |
| **可扩展点** | 实现 IHook.invoke(phase, *args, **kwargs)；register_hook(phase, callback) 注册函数；HookPhase 覆盖全生命周期。 |

## 11.3 Config 工作逻辑与要点（config/types.py）

| 项目 | 说明 |
|------|------|
| **字段** | mcp_paths, allowmcps, allowtools；workspace_dir, user_dir；default_prompt_id, initial_skill_path；knowledge: {type, storage, options}；components: {planner, validator, tool, ...}.disabled / .entries。 |
| **用途** | Builder 与各 Manager 用 Config 解析 MCP 路径、允许的 MCP/工具、Prompt 默认 ID、Skill 初始路径、Knowledge 配置、组件启用/禁用。 |
| **与上下游** | 上游：Builder with_config(config)；FileConfigProvider 等从文件加载。下游：_effective_config()、_manager_config() 供 _resolved_tools、_resolve_sys_prompt、create_knowledge、load_planner/validator 等使用。 |
| **可扩展点** | 扩展 Config 字段；实现 IConfigProvider；components.entries 支持多实例配置。 |

---

# P12：MCP 模块设计

## 12.1 配置加载工作逻辑图

```
load_mcp_configs(paths, workspace_dir, user_dir)
    IF paths is None:
        paths = [workspace_dir/.dare/mcp, user_dir/.dare/mcp] or [cwd/.dare/mcp]
    loader = MCPConfigLoader(paths)
    return loader.load()
        │
        └─► FOR each base_path in _paths:
                IF 单文件: _load_file(base_path)
                ELSE: files = _scan_directory(base_path)  // .json, .yaml, .yml, .md
                     FOR file_path in files: _load_file(file_path)
            _load_file: 解析 JSON/YAML 或从 MD 代码块提取 → MCPConfigFile.from_dict → 提取 servers → MCPServerConfig 列表
```

### 12.1.1 MCP 配置加载要点说明

| 项目 | 说明 |
|------|------|
| **输入** | paths: list[str|Path] 或 None（则用 workspace_dir/user_dir/cwd 下 .dare/mcp）；Config.mcp_paths 由 Builder 传入。 |
| **输出** | list[MCPServerConfig]（name, transport, url/command, timeout_seconds 等）。 |
| **关键步骤** | MCPConfigLoader(paths).load() 扫描目录下 JSON/YAML/MD；_load_file 解析为 MCPServerConfig；无效配置打 log 跳过。 |
| **与上下游** | 上游：Builder.build() 内若 config.mcp_paths 则 load_mcp_configs → create_mcp_clients → MCPToolkit(clients).initialize()。下游：MCPToolkit.list_tools() 供 _resolved_tools 合并。 |
| **可扩展点** | 支持新文件格式或新 transport 字段；MCPConfigFile 结构可扩展。 |

## 12.2 客户端创建与 MCPTool 调用工作逻辑图

```
create_mcp_clients(configs, connect=True)
    FOR each config in configs:
        transport = StdioTransport(...) | HTTPTransport(...)  // 根据 config.transport
        client = MCPClient(name, transport, transport_type)
        IF connect: await client.connect()
    return clients

MCPTool.execute(input, context)
    return await self._client.call_tool(self._tool_name, input, context=context)
```

### 12.2.1 MCP 客户端与 MCPTool 要点说明

| 项目 | 说明 |
|------|------|
| **工具名** | `{client.name}:{tool_name}`，如 `local_math:add`；MCPToolkit.initialize() 时 full_name = f"{client.name}:{tool_name}" 作为 ITool.name。 |
| **调用链** | DareAgent _run_tool_loop → tool_gateway.invoke(capability_id, params, envelope) → ToolManager.invoke → entry.tool.execute(params, context) → MCPTool.execute → client.call_tool(tool_name, input, context)。 |
| **与上下游** | 上游：load_mcp_configs → create_mcp_clients；MCPToolkit(clients).initialize() 后 list_tools() 返回 MCPTool 列表。下游：ToolManager 注册后 invoke 时执行 MCPTool.execute。 |
| **可扩展点** | 新增 transport（如 gRPC）；IMCPClient 实现 call_tool/list_tools/connect/disconnect。 |

---

# P13：Skill 模块设计

## 13.1 FileSystemSkillLoader 工作逻辑图

```
load()
    skills = []; seen_ids = set()
    FOR each root in _paths:
        IF not root.exists(): continue
        FOR each skill_dir in _iter_skill_dirs(root):
            skill = _load_skill(skill_dir)
            IF skill and skill.id not in seen_ids: skills.append(skill); seen_ids.add(skill.id)
    return skills

_iter_skill_dirs(root)
    IF root 自身含 SKILL.md: yield root
    FOR child in root.iterdir():
        IF child.is_dir(): IF (child/SKILL.md).exists(): yield child; ELSE: yield from _iter_skill_dirs(child)

_load_skill(skill_dir)
    content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    frontmatter, body = parse_skill_md(content)  // YAML frontmatter + markdown 正文
    name = frontmatter.get("name") or skill_dir.name; description = frontmatter.get("description")
    skill_id = name.lower().replace(" ","-").replace("_","-")
    scripts = _load_scripts(skill_dir / "scripts")  // stem -> Path
    return Skill(id=skill_id, name=name, description=description, content=body, metadata=..., skill_dir=..., scripts=scripts)
```

### 13.1.1 FileSystemSkillLoader 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | 构造 FileSystemSkillLoader(*paths)；paths 为含 SKILL.md 的目录或父目录。load() 无参数。 |
| **输出** | list[Skill]（id, name, description, content, metadata, skill_dir, scripts: dict[str, Path]）。 |
| **关键步骤** | _iter_skill_dirs 递归找含 SKILL.md 的目录；_load_skill 读 SKILL.md → parse_skill_md 得 frontmatter+body → 取 name/description/id → _load_scripts(scripts/) 得 stem→Path；去重按 skill.id。 |
| **与上下游** | 上游：Builder with_skill(path) 或 config.initial_skill_path；_load_initial_skill_and_mount 用 FileSystemSkillLoader(Path(path)).load() 取第一个 skill。下游：context.set_skill(skills[0])；assemble() 时 enrich_prompt_with_skill(sys_prompt, skill)。 |
| **可扩展点** | 实现 ISkillLoader；parse_skill_md 支持其他 frontmatter 格式；scripts 目录约定可扩展。 |

## 13.2 enrich_prompt_with_skill 工作逻辑图与要点

```
enrich_prompt_with_skill(base_prompt, skill)
    sections = [base_prompt.content, f"## Skill: {skill.name}\n\n{skill.content}"]
    scripts_block = _format_scripts_for_run_command([skill])
    // 每 (skill_id/name, path): ".py" -> "python {path}", ".sh"/".bash" -> "sh {path}"
    // 行: "- **{skill.id}/{name}**: `{cmd} [args]`"
    IF scripts_block: sections.append(scripts_block)
    merged_content = "\n\n---\n\n".join(sections)
    return Prompt(prompt_id=..., role=..., content=merged_content, supported_models=..., order=...)
```

### 13.2.1 enrich_prompt_with_skill 要点说明

| 项目 | 说明 |
|------|------|
| **输入** | base_prompt: Prompt；skill: Skill（单 skill 时）或 enrich_prompt_with_skills(base_prompt, skill_paths) 多 path 时内部 loader.load() 取多个 skill。 |
| **输出** | Prompt，content 为 base_prompt.content + "## Skill: {name}\n\n{content}" + "## Available Scripts (call via run_command)\n\n- skill_id/name: `cmd [args]`" 用 "\n\n---\n\n" 拼接。 |
| **关键步骤** | Context.assemble() 中若 _current_skill 且 _sys_prompt 则 sys_prompt = enrich_prompt_with_skill(sys_prompt, skill)；脚本列表按后缀选 python/sh，供 LLM 通过 run_command 调用。 |
| **与上下游** | 上游：context._sys_prompt、context._current_skill（Builder _load_initial_skill_and_mount 或 agent.set_skill）。下游：合并后的 Prompt 作为 system 内容进入 ModelInput。 |
| **可扩展点** | 自定义 _format_scripts_for_run_command 或增加脚本类型；enrich_prompt_with_skills 支持多 path 多 skill 合并。 |

---

*文档完。所有内容均从 dare_framework 与 examples/05-dare-coding-agent-enhanced 源码推导，每个组件均包含工作逻辑图与要点说明，供 Notebook LM 生成详细 PPT 与流程图。*
