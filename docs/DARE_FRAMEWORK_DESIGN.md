# 框架设计文档

> 基于 `dare_framework/` 与 `examples/05-dare-coding-agent-enhanced/` 源码分析，可稍参考 DARE_FRAMEWORK_PPT_SOURCE.md。供导出 PDF 使用。
>
> **文档要求**：起手为层次化模块框图；每个模块包含 **工作逻辑图** 与 **设计方案**（输入/输出、关键步骤、上下游衔接、可扩展点）。

---

## 1. 框架整体架构

### 1.1 模块框图（层次化）

以下为框架全部模块的层次化框图，每框代表一个独立模块：

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  Layer 3: Builder 层                                                                   │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐                        │
│  │ DareAgentBuilder │ │ ReactAgentBuilder│ │SimpleChatAgent   │                        │
│  │                  │ │                  │ │Builder           │                        │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘                        │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  Layer 2: 编排层（Agent 实现）                                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                                       │
│  │  DareAgent  │ │ ReactAgent  │ │SimpleChat   │                                       │
│  │ 五层编排    │ │ ReAct循环   │ │Agent        │                                       │
│  └─────────────┘ └─────────────┘ └─────────────┘                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  Layer 1: 核心域组件（可插拔）                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Context  │ │  Model   │ │   Plan   │ │   Tool   │ │Knowledge │ │  Memory  │        │
│  │ 上下文   │ │ 模型适配 │ │ 计划校验 │ │ 工具调用 │ │ 知识库   │ │ STM/LTM  │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Event   │ │   Hook   │ │  Config  │ │  Skill   │ │Compression│ │ Embedding│        │
│  │ 事件日志 │ │ 扩展点   │ │ 配置     │ │ 技能     │ │ 压缩     │ │ 向量嵌入 │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐                  │
│  │   MCP    │ │   A2A    │ │ Observability│ │ Security │ │  Infra   │                  │
│  │ MCP协议  │ │Agent协议 │ │ 遥测追踪     │ │ 风险策略 │ │ 组件身份 │                  │
│  └──────────┘ └──────────┘ └──────────────┘ └──────────┘ └──────────┘                  │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  Layer 0: 边界与基础设施                                                                │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐   │
│  │ IToolGateway     │ │ IEventLog        │ │ IExecutionControl│ │ IConfigProvider  │   │
│  │ IToolManager     │ │ 审计/可重放      │ │ HITL 控制        │ │ 配置快照         │   │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘   │
│  ┌──────────────────┐ ┌──────────────────┐                                              │
│  │ITelemetryProvider│ │ISessionSummaryStore│                                            │
│  │ 遥测/Tracing     │ │ 会话摘要持久化    │                                              │
│  └──────────────────┘ └──────────────────┘                                              │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

**Mermaid 框图（供导出 PDF 时渲染）：**

```mermaid
flowchart TB
    subgraph L3["Layer 3: Builder"]
        B1[DareAgentBuilder] B2[ReactAgentBuilder] B3[SimpleChatAgentBuilder]
    end
    subgraph L2["Layer 2: 编排"]
        A1[DareAgent] A2[ReactAgent] A3[SimpleChatAgent]
    end
    subgraph L1["Layer 1: 核心域"]
        C1[Context] C2[Model] C3[Plan] C4[Tool] C5[Knowledge] C6[Memory]
        C7[Event] C8[Hook] C9[Config] C10[Skill] C11[Compression] C12[Embedding]
        C13[MCP] C14[A2A] C15[Observability] C16[Security] C17[Infra]
    end
    subgraph L0["Layer 0: 边界"]
        I1[IToolGateway] I2[IEventLog] I3[IExecutionControl] I4[IConfigProvider]
    end
    L3 --> L2 --> L1 --> L0
```

### 1.2 定位

本框架是一个**可插拔的 Agent 运行时引擎**：通过 Builder 组装 Context、Model、Plan、Tool、Knowledge、Memory 等域组件，产出多种编排策略的 Agent（如 DareAgent 五层编排、ReactAgent、SimpleChatAgent）。DareAgent 仅是其中一种**模板 Agent 实现**，不代表整个架构。

### 1.3 四层职责

| 层级 | 职责 | 源码依据 |
|------|------|----------|
| **L3 Builder** | 链式配置，注入域组件，产出 Agent 实例 | agent/_internal/builder.py |
| **L2 编排** | 实现 IAgent.run()，决定执行流程（五层/ReAct/简单） | agent/_internal/five_layer.py, react_agent.py, simple_chat.py |
| **L1 域组件** | Context、Model、Plan、Tool、Knowledge、Memory 等可插拔实现 | 各 domain/_internal/ |
| **L0 边界** | 工具调用、事件、HITL、配置等系统契约 | tool/kernel, event/kernel, config/kernel |

### 1.3 数据流总览

```mermaid
flowchart TD
    U["User Task (str \| Task)"] --> I["IAgent.run()"]
    I --> M{"模式选择"}
    M -->|planner 或 milestones| F["Full Five-Layer<br/>Session→Milestone→Plan→Execute→Tool"]
    M -->|无 planner, 有 tools| R["ReAct<br/>Execute→Tool"]
    M -->|无 planner, 无 tools| S["Simple<br/>单次 model.generate"]
    F --> O["RunResult"]
    R --> O
    S --> O
```

---

## 2. 架构详细说明

### 2.1 框架 vs Agent 实现

| 概念 | 说明 | 代表 |
|------|------|------|
| **框架** | 域接口（IContext、IModelAdapter、IPlanner、IToolGateway 等）、Builder、可插拔组件 | dare_framework/ 各 domain |
| **Agent 实现** | 具体编排策略，实现 IAgent.run() | DareAgent、ReactAgent、SimpleChatAgent |

DareAgent 使用框架提供的 Context、Plan、Tool、Model 等，实现五层循环；ReactAgent 仅用 Execute+Tool；SimpleChatAgent 仅用 Model。三者共享同一套域组件接口。

### 2.2 域组件依赖关系

```mermaid
flowchart LR
    agent[agent]
    plan[plan]
    context[context]
    model[model]
    tool[tool]
    config[config]
    memory[memory]
    knowledge[knowledge]
    skill[skill]
    compression[compression]
    hook[hook]
    event[event]
    embedding[embedding]
    mcp[mcp]
    a2a[a2a]
    observability[observability]
    security[security]
    infra[infra]

    agent --> plan
    agent --> context
    agent --> model
    agent --> tool
    agent --> config
    agent --> compression
    agent --> hook
    agent --> event
    agent --> observability
    context --> memory
    context --> knowledge
    plan --> tool
    plan --> security
    tool --> skill
    tool --> mcp
    model --> embedding
    memory --> embedding
    knowledge --> embedding
    config --> infra
    hook --> infra
    skill --> a2a
```

---

## 3. 模块说明（完整版）

### 3.1 infra（基础设施）

**工作逻辑图：**

```
Config.is_component_enabled(component)
    │
    └─► component_settings(component.component_type).disabled 中不含 component.name
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | IComponent.name、IComponent.component_type；Config.components |
| **输出** | is_component_enabled→bool；component_config(component)→Any |
| **关键步骤** | ComponentType 枚举 PLANNER/VALIDATOR/REMEDIATOR/MEMORY/MODEL_ADAPTER/TOOL/SKILL/MCP/HOOK/PROMPT/TELEMETRY；所有可插拔组件实现 IComponent |
| **与上下游** | 上游：Config、各域组件；下游：Builder 过滤 disabled 组件、per-component 配置 |
| **可扩展点** | 扩展 ComponentType |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| ComponentType | infra/component.py | 枚举：PLANNER、VALIDATOR、REMEDIATOR、MEMORY、MODEL_ADAPTER、TOOL、SKILL、MCP、HOOK、PROMPT、TELEMETRY |
| IComponent | infra/component.py | 协议：name、component_type，用于 config.is_component_enabled() 等 |

### 3.2 agent（Agent 域）

**工作逻辑图：**

```
IAgent.run(task)
    │
    ▼
execute(task) ──► 模式判断
    │
    ├─ [Full Five-Layer] ─► _run_session_loop
    │       milestones → FOR each: create_snapshot → Plan Loop → Execute Loop → Verify
    │       success: commit; fail: rollback + remediator.remediate
    │
    ├─ [ReAct] ─► stm_add(user_msg) → _run_execute_loop(None)
    │
    └─ [Simple] ─► stm_add(user_msg) → assemble → model.generate
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | Task(description, milestones?, previous_session_summary?) 或 str |
| **输出** | RunResult(success, output, errors, session_id, session_summary) |
| **关键步骤** | 模式选择（planner/milestones → Five-Layer；无 planner 有 tools → ReAct；否则 Simple）；Session 循环：config_snapshot、milestones 分解；Milestone 循环：快照→Plan→Execute→Verify→commit/rollback |
| **与上下游** | 上游：Builder 注入 model/context/planner/validator/remediator/tool_gateway；下游：Context.assemble、Model.generate、IToolGateway.invoke、IValidator.verify_milestone |
| **可扩展点** | 实现 IAgentOrchestration、IPlanAttemptSandbox；继承 _BaseAgentBuilder 实现 _build_impl() |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| IAgent | agent/kernel.py | 运行时入口 `run(task: str \| Task, deps) -> RunResult` |
| IAgentOrchestration | agent/interfaces.py | 可插拔编排策略 `execute(task, deps) -> RunResult` |
| ISessionSummaryStore | agent/types.py | 会话摘要持久化 `save(SessionSummary)` |
| **基类与实现** | | |
| BaseAgent | agent/base_agent.py | 抽象基类，提供 set_skill/clear_skill/current_skill、run 委托 _execute |
| DareAgent | agent/_internal/five_layer.py | 五层编排：Session→Milestone→Plan→Execute→Tool；支持 ReAct/Simple 降级 |
| ReactAgent | agent/_internal/react_agent.py | ReAct 工具循环：assemble→model.generate→tool_calls→gateway.invoke |
| SimpleChatAgent | agent/_internal/simple_chat.py | 单次对话：assemble→model.generate，无工具循环 |
| **Builder** | | |
| DareAgentBuilder / ReactAgentBuilder / SimpleChatAgentBuilder | agent/_internal/builder.py | 链式配置 with_model/add_tools/with_planner 等，产出对应 Agent |
| **内部** | | |
| SessionState / MilestoneState / SessionContext | agent/_internal/orchestration.py | 会话与里程碑状态；current_milestone_state、attempts、reflections、evidence_collected |
| DefaultPlanAttemptSandbox | agent/_internal/sandbox.py | IPlanAttemptSandbox：create_snapshot/rollback/commit，STM 快照隔离 |
| session_summary_store | agent/_internal/session_summary_store.py | ISessionSummaryStore 默认实现 |
| step_executor | agent/_internal/step_executor.py | IStepExecutor，step_driven 模式 |

### 3.3 plan（Plan 域）

**工作逻辑图：**

```
IPlanner.plan(ctx)
    │
    ├─► task_description = ctx.stm_get()[-1].content
    ├─► ModelInput(system_prompt, user_prompt) → model.generate
    ├─► _parse_response(content) → plan_data
    └─► ProposedPlan(plan_description, steps)

IValidator.validate_plan(plan, ctx)
    │
    ├─► capability_index = tool_gateway.list_capabilities()
    ├─► FOR step in plan.steps: _validate_step(step, index)
    └─► ValidatedPlan(steps with risk_level from registry)

IValidator.verify_milestone(result, ctx, plan)
    │
    └─► 基于 plan.steps.params.expected_files 或执行结果判断 success
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | plan：ctx（STM 最后消息为任务）；validate_plan：ProposedPlan、ctx；verify_milestone：RunResult、ctx、ValidatedPlan? |
| **输出** | ProposedPlan / ValidatedPlan；VerifyResult(success, errors) |
| **关键步骤** | DefaultPlanner：LLM 证据型 prompt→JSON parse→ProposedStep；RegistryPlanValidator：capability_index 校验 capability_id 存在性，从注册表派生 risk_level 覆盖 planner 输出；CompositeValidator：顺序执行，失败即返回 |
| **与上下游** | 上游：DareAgent _run_plan_loop、_verify_milestone；下游：Execute Loop 使用 ValidatedPlan；Remediator 在 verify 失败后生成反思 |
| **可扩展点** | 实现 IPlanner（覆写 plan/decompose）、IValidator（如 FileExistsValidator）、IRemediator；自定义 evidence 类型 |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **类型** | | |
| Task | plan/types.py | description、task_id、milestones、previous_session_summary；to_milestones() |
| Milestone | plan/types.py | milestone_id、description、success_criteria |
| ProposedPlan / ProposedStep | plan/types.py | 非可信规划（来自 LLM） |
| ValidatedPlan / ValidatedStep | plan/types.py | 可信规划，含 risk_level（来自注册表） |
| VerifyResult / Evidence | plan/types.py | 验证结果；Evidence 含 evidence_id、evidence_type、source、data |
| DecompositionResult / RunResult / Envelope / ToolLoopRequest | plan/types.py | 任务分解结果；运行结果；工具调用边界 |
| **接口** | | |
| IPlanner | plan/interfaces.py | plan(ctx)→ProposedPlan；decompose(task, ctx)→DecompositionResult |
| IValidator | plan/interfaces.py | validate_plan(plan, ctx)→ValidatedPlan；verify_milestone(result, ctx, plan)→VerifyResult |
| IRemediator | plan/interfaces.py | remediate(verify_result, ctx)→str（反思文本） |
| IPlanAttemptSandbox | plan/interfaces.py | create_snapshot/rollback/commit |
| IStepExecutor / IEvidenceCollector | plan/interfaces.py | 单步执行；证据收集 |
| **实现** | | |
| DefaultPlanner | plan/_internal/default_planner.py | LLM 证据型规划，DEFAULT_PLAN_SYSTEM_PROMPT，_parse_response/_fallback_plan |
| RegistryPlanValidator | plan/_internal/registry_validator.py | 基于 IToolGateway 能力列表校验 capability_id，派生 risk_level |
| CompositeValidator | plan/_internal/composite_validator.py | 多校验器顺序执行，失败即返回 |
| DefaultRemediator | plan/_internal/default_remediator.py | LLM 反思，DEFAULT_REFLECT_SYSTEM_PROMPT，_fallback_reflection |

### 3.4 context（Context 域）

**工作逻辑图：**

```
Context.assemble()
    │
    ├─► messages = stm_get()
    ├─► tools = listing_tools()  (list_tool_defs 优先)
    ├─► sys_prompt = _sys_prompt
    ├─► for skill in _loaded_full_skills: sys_prompt = enrich_prompt_with_skill(sys_prompt, skill)
    └─► AssembledContext(messages, sys_prompt, tools, metadata)
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | stm_add、budget_use、set_skill、add_loaded_full_skill；listing_tools 从 tool_provider 拉取 |
| **输出** | AssembledContext(messages, sys_prompt, tools, metadata) |
| **关键步骤** | STM 为消息源；auto_skill_mode 下 _loaded_full_skills 动态合并进 sys_prompt；persistent_skill_mode 下 sys_prompt 在 build 时已合并 |
| **与上下游** | 上游：Builder 注入 tool_provider、sys_prompt；下游：ModelInput(messages, tools) |
| **可扩展点** | 覆写 assemble() 自定义 LTM/Knowledge 拼接；自定义 IRetrievalContext |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| IContext | context/kernel.py | id、short_term_memory、long_term_memory、knowledge、budget、config；stm_add/stm_get/stm_clear；budget_use/budget_check/budget_remaining；listing_tools；assemble；compress；config_update |
| IRetrievalContext | context/kernel.py | get(query, **kwargs)→list[Message]，STM/LTM/Knowledge 统一检索 |
| **实现** | | |
| Context | context/_internal/context.py | 默认实现；_tool_provider、_sys_prompt、_current_skill、_loaded_full_skills；assemble 合并 sys_prompt 与 skill |
| **类型** | | |
| Message | context/types.py | role、content、name、metadata |
| Budget | context/types.py | max_tokens/max_cost/max_time_seconds/max_tool_calls；used_* |
| AssembledContext | context/types.py | messages、sys_prompt、tools、metadata |

### 3.5 tool（Tool 域）

**工作逻辑图：**

```
ToolManager.invoke(capability_id, params, envelope)
    │
    ├─► allowed_capability_ids 校验
    ├─► entry = _registry[capability_id]
    ├─► context = context_factory()
    └─► entry.tool.execute(params, context) → ToolResult

list_tool_defs()
    └─► 遍历 _registry → OpenAI function 格式 + metadata
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | register_tool(ITool)；invoke(capability_id, params, envelope)；list_tool_defs() |
| **输出** | CapabilityDescriptor；ToolResult(success, output, error, evidence)；list[ToolDefinition] |
| **关键步骤** | 注册时 _descriptor_from_tool 生成 CapabilityDescriptor（含 risk_level、requires_approval）；invoke 前 envelope 权限校验；证据 evidence 回传 milestone_state |
| **与上下游** | 上游：Builder 注册 explicit + auto_skill + MCP + manager 工具；下游：ModelInput.tools、Execute Loop 调用 invoke |
| **可扩展点** | 实现 ITool、IToolProvider；IExecutionControl 用于 HITL；新 transport 实现 IMCPClient |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| IToolGateway | tool/kernel.py | list_capabilities()；invoke(capability_id, params, envelope) |
| IToolManager | tool/kernel.py | 继承 IToolGateway；load_tools、register_tool、list_tool_defs、invoke |
| IExecutionControl | tool/kernel.py | poll、poll_or_raise、pause、resume、checkpoint、wait_for_human |
| ITool | tool/interfaces.py | name、description、input_schema、output_schema、risk_level、requires_approval、capability_kind、execute |
| IToolProvider | tool/interfaces.py | list_tools()→list[ITool] |
| IMCPClient | tool/interfaces.py | connect、disconnect、list_tools、call_tool |
| **实现** | | |
| ToolManager | tool/_internal/managers/tool_manager.py | 注册表 _registry；register_tool、invoke、list_tool_defs；支持 IToolProvider |
| MCPToolkit | tool/_internal/toolkits/mcp_toolkit.py | IToolProvider，包装 MCP 客户端，工具名 server:tool |
| DefaultExecutionControl / FileExecutionControl | tool/_internal/control/ | IExecutionControl 实现 |
| NativeToolProvider / NoOpMCPClient | tool/_internal/providers/, adapters/ | 工具提供者；空 MCP 客户端 |
| **内置工具** | tool/_internal/tools/ | ReadFileTool、WriteFileTool、SearchCodeTool、RunCommandTool、EditLineTool、EchoTool、NoopTool、NoOpSkill |
| **类型** | | |
| CapabilityDescriptor | tool/types.py | id、name、description、input_schema、metadata（risk_level、requires_approval） |
| ToolResult | tool/types.py | success、output、error、evidence |
| RunContext | tool/types.py | deps、run_id、task_id、milestone_id、metadata、config |
| CapabilityKind / RiskLevelName | tool/types.py | TOOL、SKILL、PLAN_TOOL；read_only、idempotent_write 等 |
| **工具** | tool/_internal/utils/ | file_utils（resolve_workspace_roots）、ids（generate_id）、run_context_state |

### 3.6 model（Model 域）

**工作逻辑图：**

```
IModelAdapter.generate(model_input)
    │
    ├─► messages = _serialize_messages(model_input.messages)
    ├─► api_params = {model, messages, tools?, extra?, options?}
    └─► client.chat.completions.create(**api_params) → ModelResponse(content, tool_calls, usage)

_resolve_sys_prompt(model)
    ├─► prompt_id = override | config.default_prompt_id | "base.system"
    └─► LayeredPromptStore.get(prompt_id, model=model.name)
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | ModelInput(messages, tools, metadata)；GenerateOptions(temperature, max_tokens 等) |
| **输出** | ModelResponse(content, tool_calls, usage) |
| **关键步骤** | OpenRouter/OpenAI 用 AsyncOpenAI；_serialize_messages 转 OpenAI 格式；Prompt 叠加 workspace+user+builtin |
| **与上下游** | 上游：Context.assemble()；下游：Execute Loop 解析 tool_calls、Tool Loop 调用 |
| **可扩展点** | 实现 IModelAdapter；DefaultModelAdapterManager 从 Config.llm 解析 |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| IModelAdapter | model/kernel.py | generate(model_input, options)→ModelResponse |
| IModelAdapterManager | model/interfaces.py | load_model_adapter(config)→IModelAdapter |
| IPromptStore | model/interfaces.py | get(prompt_id, model, version)→Prompt |
| **实现** | | |
| OpenRouterModelAdapter | model/_internal/openrouter_adapter.py | OpenAI Async SDK，支持 OpenRouter |
| OpenAIModelAdapter | model/_internal/openai_adapter.py | LangChain ChatOpenAI，自定义 endpoint |
| DefaultModelAdapterManager | model/_internal/default_model_adapter_manager.py | 基于 Config.llm 解析 |
| LayeredPromptStore | model/_internal/layered_prompt_store.py | 叠加 FileSystem+User+Builtin Prompt |
| BuiltInPromptLoader / FileSystemPromptLoader | model/_internal/ | 内置与文件系统 Prompt 加载 |
| **工厂** | model/factories.py | create_default_model_adapter_manager、create_default_prompt_store |
| **类型** | | |
| ModelInput | model/types.py | messages、tools、metadata |
| ModelResponse | model/types.py | content、tool_calls、usage |
| Prompt | model/types.py | prompt_id、role、content、supported_models、order |

### 3.7 config（Config 域）

**工作逻辑图：**

```
FileConfigProvider._load_config()
    │
    ├─► user_layer = _load_layer(user_dir / .dare/config.json)
    ├─► workspace_layer = _load_layer(workspace_dir / .dare/config.json)
    ├─► merged = _deep_merge(user_layer, workspace_layer)
    └─► Config.from_dict(merged)
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | workspace_dir、user_dir；.dare/config.json 分层 |
| **输出** | Config（llm、mcp_paths、allowtools、allowmcps、knowledge、long_term_memory、skill_mode 等） |
| **关键步骤** | user 层优先，workspace 覆盖；_deep_merge 递归合并嵌套 dict；component_settings 用于 is_component_enabled |
| **与上下游** | 上游：Builder.with_config；下游：create_long_term_memory、create_knowledge、load_mcp_toolkit、LayeredPromptStore |
| **可扩展点** | 实现 IConfigProvider；扩展 Config 字段 |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| IConfigProvider | config/kernel.py | current()、reload()→Config |
| **实现** | | |
| FileConfigProvider | config/_internal/file_config_provider.py | 从 user_dir、workspace_dir 读取 .dare/config.json，分层合并 |
| **工厂** | config/factory.py | build_config_provider(workspace_dir, user_dir) |
| **类型** | | |
| Config | config/types.py | llm、mcp_paths、allowtools、allowmcps、knowledge、long_term_memory、workspace_dir、user_dir、prompt_store_path_pattern、default_prompt_id、skill_mode、initial_skill_path、skill_paths、observability、a2a；component_settings、is_component_enabled |
| LLMConfig / ProxyConfig | config/types.py | adapter、endpoint、api_key、model、proxy |
| ComponentConfig / ObservabilityConfig | config/types.py | disabled、entries；enabled、exporter、otlp_endpoint、sampling_ratio |

### 3.8 memory（Memory 域）

**工作逻辑图：**

```
InMemorySTM: add → _messages.append; get → list(_messages); compress(max_messages) → 保留最近 N 条

RawDataLongTermMemory.get(query): storage.search(query, top_k) → _record_to_message

VectorLongTermMemory.get(query): embed(query) → vector_store.search → _document_to_message
VectorLongTermMemory.persist(messages): embed_batch → vector_store.add_batch
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | STM：add(Message)；LTM：get(query, top_k)、persist(messages) |
| **输出** | get()→list[Message]；compress()→移除条数 |
| **关键步骤** | RawData 用 IRawDataStore.substring 检索；Vector 用 IEmbeddingAdapter + IVectorStore；create_long_term_memory 按 config.type 选择实现 |
| **与上下游** | 上游：Context 持有；下游：assemble 可选检索 LTM（默认不自动） |
| **可扩展点** | 实现 IShortTermMemory/ILongTermMemory；自定义 storage 后端 |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| IShortTermMemory | memory/kernel.py | 继承 IRetrievalContext；add、get、clear、compress |
| ILongTermMemory | memory/kernel.py | 继承 IRetrievalContext；get、persist |
| **实现** | | |
| InMemorySTM | memory/_internal/in_memory_stm.py | 列表存储，compress 保留最近 N 条 |
| RawDataLongTermMemory | memory/_internal/rawdata_ltm.py | 基于 IRawDataStore，substring 检索 |
| VectorLongTermMemory | memory/_internal/vector_ltm.py | 基于 IEmbeddingAdapter + IVectorStore，向量检索 |
| **工厂** | memory/factory.py | create_long_term_memory(config, embedding_adapter)，支持 rawdata/vector、in_memory/sqlite/chromadb |

### 3.9 knowledge（Knowledge 域）

**工作逻辑图：**

```
RawDataKnowledge.get(query): storage.search(query, top_k) → Message(content, metadata)
RawDataKnowledge.add(content): storage.add(content, metadata)

VectorKnowledge.get(query): embed(query) → vector_store.search → Message + similarity
VectorKnowledge.add(content): embed(content) → vector_store.add

Builder._register_tools_with_manager() ──► if knowledge: register KnowledgeGetTool / KnowledgeAddTool
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | get(query, top_k?)；add(content, metadata?)；Builder 注入 knowledge |
| **输出** | get→list[Message]；knowledge_get/knowledge_add 作为工具暴露 |
| **关键步骤** | create_knowledge 按 config.type 选择 RawData/Vector；Vector 需 embedding_adapter |
| **与上下游** | 上游：Builder/Config；下游：ToolManager 注册；模型可调用 knowledge_get/add |
| **可扩展点** | 实现 IKnowledge；自定义 storage/vector_store |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| IKnowledge | knowledge/kernel.py | 继承 IRetrievalContext；get、add |
| **实现** | | |
| RawDataKnowledge | knowledge/_internal/rawdata_knowledge/ | 基于 IRawDataStore，substring 检索；storage 可选 InMemoryRawDataStorage、SQLiteRawDataStorage |
| VectorKnowledge | knowledge/_internal/vector_knowledge/ | 基于 IEmbeddingAdapter + IVectorStore；InMemoryVectorStore、SQLiteVectorStore、ChromaDBVectorStore |
| KnowledgeGetTool / KnowledgeAddTool | knowledge/_internal/knowledge_tools.py | 框架自动注册为 knowledge_get、knowledge_add |
| **工厂** | knowledge/factory.py | create_knowledge(config, embedding_adapter) |

### 3.10 skill（Skill 域）

**工作逻辑图：**

```
persistent_skill_mode:
  build() ──► FileSystemSkillLoader.load() ──► context.set_skill(skill)
  sys_prompt = enrich_prompt_with_skill(sys_prompt, skill)

auto_skill_mode:
  build() ──► SkillStore.reload() ──► sys_prompt = enrich_prompt_with_skill_summaries(sys_prompt, skills)
  tools += SearchSkillTool + SkillScriptRunner
  运行时: search_skill(skill_id) ──► context.add_loaded_full_skill(skill)
  assemble() ──► sys_prompt + full skill content
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | initial_skill_path / skill_paths；SKILL.md（YAML frontmatter + body + scripts/） |
| **输出** | persistent：sys_prompt 含完整 skill；auto：sys_prompt 含摘要，search_skill 加载完整内容 |
| **关键步骤** | FileSystemSkillLoader 扫描 SKILL.md；SearchSkillTool 将 Skill 存入 Context._loaded_full_skills；assemble 合并进 sys_prompt |
| **与上下游** | 上游：Builder、Config.skill_mode；下游：Context.assemble、run_skill_script |
| **可扩展点** | ISkillLoader、ISkillSelector（如 KeywordSkillSelector） |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **类型** | | |
| Skill | skill/types.py | id、name、description、content、scripts；to_context_section、get_script_path |
| **接口** | | |
| ISkillLoader | skill/interfaces.py | load()→list[Skill] |
| ISkillSelector | skill/interfaces.py | select(task_description, skills)→list[Skill] |
| **实现** | | |
| FileSystemSkillLoader | skill/_internal/filesystem_skill_loader.py | 扫描 SKILL.md，解析 YAML frontmatter + body，scripts/ 目录 |
| KeywordSkillSelector | skill/_internal/keyword_skill_selector.py | 按关键字筛选技能 |
| SkillStore | skill/_internal/skill_store.py | 加载、索引、select_for_task |
| SearchSkillTool | skill/_internal/search_skill_tool.py | 根据 skill_id 将完整 Skill 注入 Context |
| SkillScriptRunner | skill/_internal/skill_script_runner.py | run_skill_script(skill_id, script_name, args) |
| prompt_enricher | skill/_internal/prompt_enricher.py | enrich_prompt_with_skill、enrich_prompt_with_skill_summaries |

### 3.11 compression（Compression 域）

**工作逻辑图：**

```
compress_context(ctx, phase, max_messages, strategy?)
    │
    ├─► strategy=summary_preview: _build_summary_preview(messages) → 摘要 + tail
    ├─► strategy=dedup_then_truncate: _dedup_messages(messages) → 去重
    └─► truncate: 保留最近 max_messages 条
    stm_clear() + stm_add(消息)

compress_context_llm_summary(ctx, model, max_messages, keep_tail)
    │
    ├─► head = messages[:-keep_tail]; tail = messages[-keep_tail:]
    ├─► ModelInput(summary_prompt, conversation_text) → model.generate
    └─► stm_clear() + stm_add(summary_msg) + stm_add(tail)
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | ctx、phase、max_messages；strategy：truncate/dedup_then_truncate/summary_preview |
| **输出** | 就地修改 ctx.stm，无返回值 |
| **关键步骤** | _dedup_messages 按 (role, content) 去重；_build_summary_preview 启发式摘要；llm_summary 调用模型生成语义摘要 |
| **与上下游** | 上游：Agent 在 plan/execute/react/simple_chat 各阶段调用；下游：减少 context 长度，适配模型窗口 |
| **可扩展点** | 新增 strategy；自定义 _build_summary_preview |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| compress_context | compression/core.py | 同步轻量压缩：truncate、dedup_then_truncate、summary_preview；_dedup_messages、_build_summary_preview |
| compress_context_llm_summary | compression/core.py | 异步 LLM 语义摘要压缩；保留 keep_tail 条，将更早消息摘要为一条 system 消息 |

### 3.12 hook（Hook 域）

**工作逻辑图：**

```
HookExtensionPoint.emit(phase, payload)
    │
    ├─► callbacks = _callbacks.get(phase)
    │       FOR callback: callback(payload)  # 同步
    └─► FOR hook in _hooks: await hook.invoke(phase, payload=payload)  # 异步，best-effort
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | HookPhase + payload（task_id、run_id、budget_stats、duration_ms 等） |
| **输出** | 无强制返回值；异常仅日志，不中断主流程 |
| **关键步骤** | DareAgent 在 BEFORE/AFTER_RUN、SESSION、MILESTONE、PLAN、EXECUTE、CONTEXT_ASSEMBLE、MODEL、TOOL、VERIFY 各阶段 emit |
| **与上下游** | 上游：Agent 生命周期；下游：ObservabilityHook 记录 span/metric；IHookManager 从 Config 加载 |
| **可扩展点** | 实现 IHook（如审批、审计、指标）；register_hook(phase, callback) |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| IHook | hook/kernel.py | invoke(phase, *args, **kwargs)，best-effort |
| IExtensionPoint | hook/kernel.py | register_hook(phase, hook)、emit(phase, payload) |
| IHookManager | hook/interfaces.py | load_hooks(config)→list[IHook] |
| **实现** | | |
| HookExtensionPoint | hook/_internal/hook_extension_point.py | 分发到 callbacks 与 hooks；异常仅日志 |
| **类型** | | |
| HookPhase | hook/types.py | BEFORE/AFTER_RUN、SESSION、MILESTONE、PLAN、EXECUTE、CONTEXT_ASSEMBLE、MODEL、TOOL、VERIFY |

### 3.13 event（Event 域）

**工作逻辑图：**

```
IEventLog.append(event_type, payload)
    │
    └─► 追加事件记录，返回 event_id

query(filter, limit) → list[Event]
replay(from_event_id) → RuntimeSnapshot
verify_chain() → bool
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | append(event_type, payload)；query(filter, limit) |
| **输出** | event_id；list[Event]；RuntimeSnapshot |
| **关键步骤** | DareAgent._log_event 在 session/milestone/plan/tool 各阶段 append；TraceAwareEventLog 自动附带 trace_id |
| **与上下游** | 上游：DareAgentBuilder.with_event_log；下游：审计、重放、验证链 |
| **可扩展点** | 实现 IEventLog；WORM 存储、哈希链 |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| IEventLog | event/kernel.py | append(event_type, payload)→event_id；query、replay、verify_chain |
| Event | event/types.py | event_type、payload、event_id、timestamp、prev_hash、event_hash |
| RuntimeSnapshot | event/types.py | from_event_id、events |

### 3.14 embedding（Embedding 域）

**工作逻辑图：**

```
IEmbeddingAdapter.embed(text)
    └─► client.aembed_query(text) → EmbeddingResult(vector, metadata)

embed_batch(texts) → list[EmbeddingResult]
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | embed(text, options)；embed_batch(texts, options) |
| **输出** | EmbeddingResult(vector, metadata) |
| **关键步骤** | OpenAIEmbeddingAdapter 用 LangChain OpenAIEmbeddings；支持 OpenAI/Azure/自定义 endpoint |
| **与上下游** | 上游：Builder.with_embedding_adapter；下游：VectorKnowledge、VectorLongTermMemory |
| **可扩展点** | 实现 IEmbeddingAdapter |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| IEmbeddingAdapter | embedding/interfaces.py | embed(text, options)→EmbeddingResult；embed_batch(texts, options)→list[EmbeddingResult] |
| **实现** | | |
| OpenAIEmbeddingAdapter | embedding/_internal/openai_embedding.py | LangChain OpenAIEmbeddings，支持 OpenAI/Azure/自定义 endpoint |
| **类型** | | |
| EmbeddingResult | embedding/types.py | vector、metadata |
| EmbeddingOptions | embedding/types.py | model、metadata |

### 3.15 mcp（MCP 域）

**工作逻辑图：**

```
load_mcp_toolkit(config)
    │
    ├─► load_mcp_configs(paths, workspace_dir, user_dir) → list[MCPServerConfig]
    ├─► create_mcp_clients(configs, connect=True) → list[IMCPClient]
    └─► MCPToolkit(clients).initialize() → list_tools() 工具名 server:tool
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | Config.mcp_paths、allowmcps；JSON/YAML/MD 配置 |
| **输出** | MCPToolkit(IToolProvider)，list_tools() 返回 MCPTool 列表 |
| **关键步骤** | 路径解析（workspace_dir 相对）；stdio→StdioTransport，http→HTTPTransport；connect→list_tools→full_name=server:tool |
| **与上下游** | 上游：Builder.build() 在 config.mcp_paths 时自动调用；下游：_resolved_tools 合并 MCP 工具→ToolManager 注册 |
| **可扩展点** | 新 transport（grpc）；实现 IMCPClient |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| MCPConfigLoader | mcp/loader.py | 扫描 JSON/YAML/MD 配置，load()→list[MCPServerConfig] |
| load_mcp_configs | mcp/loader.py | 封装 MCPConfigLoader，路径解析、workspace_dir 相对路径 |
| MCPClientFactory | mcp/factory.py | create(config)→IMCPClient；stdio→StdioTransport，http→HTTPTransport；grpc 未实现 |
| create_mcp_clients | mcp/factory.py | 批量创建并可选 connect |
| MCPClient | mcp/client.py | 包装 ITransport，connect、list_tools、call_tool |
| StdioTransport / HTTPTransport | mcp/transports/ | stdio 子进程；http POST |
| MCPServerConfig / TransportType | mcp/types.py | name、transport、command、url、timeout_seconds |

### 3.16 a2a（A2A 域）

**工作逻辑图：**

```
create_a2a_app(card, agent.run)
    │
    ├─► GET /.well-known/agent.json → AgentCard
    └─► POST JSON-RPC
          tasks/send: message_parts_to_user_input(parts) → Task → agent.run → run_result_to_artifact_dict
          tasks/get: 返回 TaskState
          tasks/cancel: 标记 cancelled
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | A2A Message.parts（text/file）；Task(description) |
| **输出** | TaskStateDict（status、artifacts）；ArtifactDict（parts: text/file） |
| **关键步骤** | message_parts_to_user_input 将 text/file 转为 Task.description；run_result_to_artifact_dict 将 RunResult 转为 Artifact；inlineData base64 或 URI |
| **与上下游** | 上游：Config.a2a、Skill 构建 AgentCard；下游：A2AClient 发现与调用 |
| **可扩展点** | 自定义 message_adapter、auth_validate |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **类型** | a2a/types.py | AgentCardDict、AgentSkillDict、MessageDict、PartDict、TaskStateDict、ArtifactDict、TextPartDict、FilePartInlineDict、FilePartUriDict |
| build_agent_card | a2a/server/agent_card.py | 从 Config.a2a + Skill 构建 AgentCard |
| create_a2a_app | a2a/server/transport.py | GET /.well-known/agent.json→AgentCard；POST JSON-RPC |
| handle_tasks_send / handle_tasks_get / handle_tasks_cancel | a2a/server/handlers.py | tasks/send 调用 agent.run(Task)，RunResult→Artifact；tasks/get、tasks/cancel |
| message_parts_to_user_input / run_result_to_artifact_dict | a2a/server/message_adapter.py | A2A Message↔Task/RunResult 适配 |
| A2AClient / discover_agent_card | a2a/client/ | 发现与调用远程 Agent |

### 3.17 observability（Observability 域）

**工作逻辑图：**

```
ObservabilityHook.invoke(phase, payload)
    │
    ├─► BEFORE_RUN: start_span("run")
    ├─► BEFORE/AFTER_SESSION/MILESTONE/PLAN/EXECUTE/MODEL/TOOL/VERIFY: span + attributes
    ├─► payload.budget_stats → MetricsCollector.record_budget
    └─► AFTER_RUN: end_span, record metrics
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | Hook payload（task_id、run_id、budget_stats、duration_ms、model_usage 等） |
| **输出** | Traces（OTel span）、Metrics（budget、error 等） |
| **关键步骤** | OTelTelemetryProvider 使用 OpenTelemetry；DareAgent 在 telemetry 为 OTel 时自动注入 ObservabilityHook；make_trace_aware 为 EventLog 附带 trace_id |
| **与上下游** | 上游：HookExtensionPoint.emit；下游：OTLP exporter、Console exporter |
| **可扩展点** | 实现 ITelemetryProvider；ObservabilityConfig（采样、脱敏） |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| **接口** | | |
| ITelemetryProvider | observability/kernel.py | start_span、record_metric、record_event、shutdown |
| ISpan | observability/kernel.py | set_attribute、add_event、set_status、end |
| **实现** | | |
| OTelTelemetryProvider | observability/_internal/otel_provider.py | OpenTelemetry，OTLP/Console exporter；GenAIAttributes、DAREAttributes |
| NoOpTelemetryProvider | observability/_internal/otel_provider.py | 空实现 |
| ObservabilityHook | observability/_internal/tracing_hook.py | IHook，监听 HookPhase，记录 span/metric |
| make_trace_aware | observability/_internal/event_trace_bridge.py | EventLog 自动附带 trace_id |
| MetricsCollector | observability/_internal/metrics_collector.py | 采集 budget、error 等 |

### 3.18 security（Security 域）

**工作逻辑图：**

```
ValidatedStep 的 risk_level 来自 RegistryPlanValidator 从 CapabilityDescriptor.metadata 解析
TrustedInput: params + risk_level + metadata（可信来源覆盖 planner 输出）
```

**设计方案要点：**

| 项目 | 说明 |
|------|------|
| **输入** | CapabilityDescriptor.metadata.risk_level；ProposedStep（不可信） |
| **输出** | ValidatedStep.risk_level（READ_ONLY/IDEMPOTENT_WRITE/COMPENSATABLE/NON_IDEMPOTENT_EFFECT）；PolicyDecision |
| **关键步骤** | RegistryPlanValidator 从 IToolGateway 能力列表取 risk_level 覆盖 planner；TrustedInput 表示可信派生结果 |
| **与上下游** | 上游：ITool 注册时指定 risk_level；下游：Envelope、IExecutionControl、requires_approval |
| **可扩展点** | 扩展 RiskLevel；实现 Policy 决策 |

**组件清单：**

| 组件 | 路径 | 职责 |
|------|------|------|
| RiskLevel | security/types.py | READ_ONLY、IDEMPOTENT_WRITE、COMPENSATABLE、NON_IDEMPOTENT_EFFECT |
| PolicyDecision | security/types.py | ALLOW、DENY、APPROVE_REQUIRED |
| TrustedInput / SandboxSpec | security/types.py | 可信输入与沙箱规格占位 |

### 3.19 模块总览

| 域 | 主要职责 | 关键接口/实现 |
|------|----------|---------------|
| **infra** | 组件身份（ComponentType、IComponent） | 跨域配置与启用/禁用 |
| **agent** | 编排与 Builder | IAgent、IAgentOrchestration、DareAgent、ReactAgent、SimpleChatAgent、*Builder |
| **plan** | 规划、校验、修复 | IPlanner、IValidator、IRemediator、DefaultPlanner、RegistryPlanValidator、DefaultRemediator |
| **context** | 上下文组装 | IContext、Context、assemble、STM/LTM/Knowledge |
| **tool** | 工具注册与调用 | IToolGateway、IToolManager、ToolManager、MCPToolkit、IExecutionControl |
| **model** | 模型适配与 Prompt | IModelAdapter、OpenRouter/OpenAI 适配器、LayeredPromptStore |
| **config** | 配置提供 | IConfigProvider、FileConfigProvider、Config |
| **memory** | 短期/长期记忆 | IShortTermMemory、ILongTermMemory、InMemorySTM、RawData/Vector LTM |
| **knowledge** | 知识检索 | IKnowledge、RawData/Vector Knowledge、knowledge_get/add |
| **skill** | 技能加载与注入 | Skill、FileSystemSkillLoader、SkillStore、SearchSkillTool、SkillScriptRunner |
| **compression** | 上下文压缩 | compress_context、compress_context_llm_summary |
| **hook** | 生命周期扩展 | IHook、HookExtensionPoint、HookPhase |
| **event** | 事件审计 | IEventLog、Event、RuntimeSnapshot |
| **embedding** | 向量嵌入 | IEmbeddingAdapter、OpenAIEmbeddingAdapter |
| **mcp** | MCP 协议 | MCPConfigLoader、MCPClient、Stdio/HTTP transport |
| **a2a** | Agent-to-Agent 协议 | AgentCard、tasks/send、Message/Artifact 适配 |
| **observability** | 遥测与追踪 | ITelemetryProvider、OTelTelemetryProvider、ObservabilityHook |
| **security** | 风险与策略 | RiskLevel、PolicyDecision |

---

## 4. 设计原理

### 4.1 可插拔与分层

- **L3 Builder**：开发者通过链式 API 注入组件，不关心内部组装顺序。
- **L2 编排**：Agent 实现只依赖域接口（IContext、IModelAdapter、IPlanner 等），可替换。
- **L1 域组件**：各域独立实现接口，如替换 IPlanner、IValidator 不影响其他域。
- **L0 边界**：IToolGateway、IEventLog 等划定系统边界，便于审计与扩展。

### 4.2 可信与不可信分离

- ProposedPlan / ProposedStep 来自 LLM，不可信。
- ValidatedPlan / ValidatedStep 由 IValidator 基于能力注册表派生 risk_level 等，作为可信来源。
- RegistryPlanValidator 从 IToolGateway 获取能力列表，校验 capability_id 并覆盖安全字段。

### 4.3 状态隔离

- IPlanAttemptSandbox 对 STM 做快照/回滚/提交。
- 每次 milestone 尝试前快照，验证失败或遇到 plan tool 时回滚，保证失败不污染上下文。

---

## 5. 算法说明

### 5.1 上下文压缩（compression/core.py）

- **truncate**：保留最近 max_messages 条。
- **dedup_then_truncate**：先按 (role, content) 去重，再截断。
- **summary_preview**：较早消息折叠为一条 system 启发式摘要，保留最近若干条。
- **compress_context_llm_summary**：异步调用模型做语义摘要压缩。

### 5.2 计划校验（RegistryPlanValidator）

1. 从 IToolGateway 构建 capability_index（id/alias 映射）。
2. 遍历 plan.steps：capability_id 以 `plan:` 开头则直接通过；否则从注册表解析 capability，取 risk_level，构造 ValidatedStep。
3. 未知 capability 加入 errors，返回 ValidatedPlan(success=False)。

### 5.3 验证（FileExistsValidator 示例）

1. 从 plan.steps 的 params.expected_files 收集期望文件，若无则用构造时 expected_files。
2. 遍历期望文件，检查 workspace 内是否存在。
3. 缺失则 VerifyResult(success=False)；全存在则 VerifyResult(success=True)。

---

## 6. 流程图

### 6.1 Builder 构建流程

```mermaid
flowchart TD
    A["build()"] --> B{"config.mcp_paths?"}
    B -->|是| C["load_mcp_toolkit"]
    B -->|否| D["_build_impl"]
    C --> D
    D --> E["_resolved_model"]
    D --> F["_resolved_tools"]
    D --> G["_ensure_tool_manager"]
    D --> H["_register_tools_with_manager"]
    D --> I["_load_initial_skill / _load_skills_for_auto_mode"]
    D --> J["解析 planner/validators/remediator"]
    D --> K["构造 Agent"]
```

### 6.2 DareAgent 五层编排（一种编排策略）

```mermaid
flowchart TB
    subgraph Session["Session Loop"]
        S1["config_snapshot + milestones"]
        S2["FOR each milestone"]
    end

    subgraph Milestone["Milestone Loop"]
        M1["create_snapshot"]
        M2["Plan Loop: planner.plan → validator.validate_plan"]
        M3["Execute Loop: assemble → model.generate → tool_calls"]
        M4["verify_milestone"]
        M5{"success?"}
        M6["commit"]
        M7["rollback + remediator.remediate"]
    end

    S1 --> S2 --> M1 --> M2 --> M3 --> M4 --> M5
    M5 -->|是| M6
    M5 -->|否| M7 --> M1
```

### 6.3 Execute Loop（通用）

```mermaid
flowchart LR
    A["compress_context"] --> B["assemble"]
    B --> C["model.generate"]
    C --> D{"tool_calls?"}
    D -->|是| E["Tool Loop: gateway.invoke"]
    E --> F["stm_add 结果"]
    F --> B
    D -->|否| G["返回 outputs"]
```

---

## 7. 类图

### 7.1 框架核心接口与编排实现

```mermaid
classDiagram
    class IAgent {
        <<interface>>
        +run(task, deps) RunResult
    }
    class IAgentOrchestration {
        <<interface>>
        +execute(task, deps) RunResult
    }
    class BaseAgent {
        <<abstract>>
        +run(task, deps) RunResult
        #_execute(task) str*
    }
    class DareAgent {
        -_model: IModelAdapter
        -_context: IContext
        -_planner: IPlanner
        -_validator: IValidator
        -_tool_gateway: IToolGateway
        +execute(task) RunResult
    }
    class ReactAgent {
        +_execute(task) str
    }
    class SimpleChatAgent {
        +_execute(task) str
    }

    IAgent <|.. DareAgent
    IAgent <|.. ReactAgent
    IAgent <|.. SimpleChatAgent
    BaseAgent <|-- DareAgent
    BaseAgent <|-- ReactAgent
    BaseAgent <|-- SimpleChatAgent
    IAgentOrchestration <|.. DareAgent
```

### 7.2 Plan 域接口与实现

```mermaid
classDiagram
    class IPlanner {
        <<interface>>
        +plan(ctx) ProposedPlan
        +decompose(task, ctx) DecompositionResult
    }
    class IValidator {
        <<interface>>
        +validate_plan(plan, ctx) ValidatedPlan
        +verify_milestone(result, ctx, plan) VerifyResult
    }
    class IRemediator {
        <<interface>>
        +remediate(verify_result, ctx) str
    }
    class DefaultPlanner {
        +plan(ctx) ProposedPlan
    }
    class RegistryPlanValidator {
        +validate_plan(plan, ctx) ValidatedPlan
    }
    class CompositeValidator {
        -_validators: list
        +validate_plan(plan, ctx) ValidatedPlan
    }
    class DefaultRemediator {
        +remediate(verify_result, ctx) str
    }

    IPlanner <|.. DefaultPlanner
    IValidator <|.. RegistryPlanValidator
    IValidator <|.. CompositeValidator
    IRemediator <|.. DefaultRemediator
```

### 7.3 Context 与 Tool 域

```mermaid
classDiagram
    class IContext {
        <<interface>>
        +stm_add(msg)
        +stm_get()
        +assemble() AssembledContext
        +listing_tools()
    }
    class Context {
        +short_term_memory
        +long_term_memory
        +knowledge
        +assemble()
    }
    class IToolGateway {
        <<interface>>
        +list_capabilities()
        +invoke(capability_id, params, envelope)
    }
    class ToolManager {
        +register_tool(tool)
        +invoke(...)
    }

    IContext <|.. Context
    IToolGateway <|.. ToolManager
```

---

## 8. 时序图

### 8.1 Agent.run() 通用时序

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent(Dare/React/SimpleChat)
    participant C as Context
    participant M as IModelAdapter
    participant T as IToolGateway

    U->>A: run(Task)
    A->>C: assemble()
    C-->>A: messages, tools
    A->>M: generate(ModelInput)
    M-->>A: content, tool_calls?
    alt 有 tool_calls
        A->>T: invoke(capability_id, params)
        T-->>A: ToolResult
        A->>C: stm_add(tool_msg)
        Note over A,C: 下一轮 assemble + generate
    else 无 tool_calls
        A-->>U: RunResult
    end
```

### 8.2 DareAgent 五层模式（Session→Milestone→Plan→Execute）

```mermaid
sequenceDiagram
    participant A as DareAgent
    participant P as IPlanner
    participant V as IValidator
    participant M as IModelAdapter
    participant T as IToolGateway

    A->>P: plan(ctx)
    P->>M: generate(...)
    M-->>P: ProposedPlan
    A->>V: validate_plan(plan)
    V-->>A: ValidatedPlan
    loop Execute Loop
        A->>M: generate(model_input)
        M-->>A: tool_calls
        A->>T: invoke(...)
        T-->>A: ToolResult
    end
    A->>V: verify_milestone(result, plan)
    V-->>A: VerifyResult
```

---

## 9. 状态图

### 9.1 Milestone 尝试状态

```mermaid
stateDiagram-v2
    [*] --> CreateSnapshot
    CreateSnapshot --> PlanLoop
    PlanLoop --> ExecuteLoop
    ExecuteLoop --> Verify
    Verify --> CommitSnapshot: success
    Verify --> RollbackSnapshot: !success
    RollbackSnapshot --> Remediate
    Remediate --> CreateSnapshot: 重试
    Remediate --> [*]: 达到 max_attempts
    CommitSnapshot --> [*]
```

### 9.2 CLI 会话状态（示例 05）

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> AWAITING_APPROVAL: /mode plan + 输入任务
    IDLE --> RUNNING: /mode execute + 输入
    AWAITING_APPROVAL --> RUNNING: /approve
    AWAITING_APPROVAL --> IDLE: /reject
    RUNNING --> IDLE: 完成
```

---

## 10. 示例：05-dare-coding-agent-enhanced

### 10.1 用途

示例展示**如何使用框架**组装一个编码 Agent：通过 DareAgentBuilder 注入 Model、Knowledge、Tools、Planner、Validator、Remediator、EventLog 等，产出 DareAgent 实例。

### 10.2 组件组装

| 组件 | 实现 |
|------|------|
| Model | OpenRouterModelAdapter |
| Tools | ReadFileTool, WriteFileTool, SearchCodeTool, RunCommandTool |
| Planner | DefaultPlanner |
| Validator | FileExistsValidator |
| Remediator | DefaultRemediator |
| Knowledge | RawDataKnowledge + InMemoryRawDataStorage |

### 10.3 FileExistsValidator 行为

- validate_plan：接受 ProposedPlan，转为 ValidatedPlan。
- verify_milestone：从 plan.steps 的 params.expected_files 提取期望文件，检查 workspace 内文件存在性。

---

## 11. PDF 导出说明

- **Typora**：打开后导出 PDF（支持 Mermaid）。
- **Pandoc**：`pandoc DARE_FRAMEWORK_DESIGN.md -o out.pdf --pdf-engine=xelatex -V CJKmainfont="SimSun"`。
- **VS Code + Markdown PDF**：右键导出 PDF。
- Mermaid 需支持 Mermaid 的渲染器；否则可先用 mermaid-cli 将图表渲染为图片再嵌入。

---

*基于 dare_framework 与 examples/05-dare-coding-agent-enhanced 源码分析。*
