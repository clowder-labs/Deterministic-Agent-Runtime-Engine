# DARE Framework 架构终稿评审 v2.1（草案）：内核化与上下文工程

> **定位声明（请先读）**：DARE 是 **framework**，不交付“某个具体 Agent 产品”。  
> DARE 交付的是一套 **Kernel + 组件体系 + 开发者 API**，开发者用它来组装不同类型的 Agent Runtime。  
> `examples/` 里的 coding agent 只是一个示例组合（composition），不是框架本体。

> **v2.0 相对 v1.3 的核心变更**：
> 1. **架构内核化**：引入 `Layer 0: Kernel`（不可变基础设施），把“策略/算法”整体下放为可插拔组件。
> 2. **上下文工程优先**：用 `IContextManager + IResourceManager` 显式管理“什么进入上下文窗口”（注意力资源）。
> 3. **协议与实现分离**：引入 `Layer 1: Protocol Adapters`（MCP/A2A/A2UI），Kernel 协议无关。
> 4. **长任务原生支持**：将 Checkpoint/暂停/恢复收敛到 `IExecutionControl`（中断控制面）。
> 5. **安全边界升级**：以 `ISecurityBoundary` 统一表达 **Trust + Policy + Sandbox**，但保留 trust/policy 子模块以避免“巨石接口”。

> **v2.1 相对 v2.0 的核心变更（本次调整点）**：
> 1. **Tool Loop 边界更清晰**：`Envelope` 只表达执行边界；工具调用 payload（`capability_id/params`）独立为 `ToolLoopRequest`。
> 2. **安全关键字段派生强化**：`risk_level`/`requires_approval` 必须来自可信 registry（`IToolGateway.list_capabilities()` 的 metadata），忽略模型/规划器自报。
> 3. **实现侧更“按域归档”**：Kernel 默认实现建议收敛到各自 domain package（避免 `core/defaults` 成为兜底大杂烩）。

---

## 目录

1. [架构全景](#一架构全景)
2. [上下文工程统一模型](#二上下文工程统一模型)
3. [五层循环模型（v2 标准化）](#三五层循环模型v2-标准化)
4. [核心接口定义（v2）](#四核心接口定义v2)
5. [核心数据结构（v2）](#五核心数据结构v2)
6. [执行流程详解（v2）](#六执行流程详解v2)
7. [组件实现清单（建议）](#七组件实现清单建议)
8. [使用示例（framework 视角）](#八使用示例framework-视角)
9. [设计决策记录（v2）](#九设计决策记录v2)
10. [附录：v1.3 → v2 术语对照与迁移点](#附录v13--v2-术语对照与迁移点)

---

## 一、架构全景

### 1.1 从 v1.3 的“三层”到 v2 的“四层”

v1.3 的结构是：
- Layer 1: Core Infrastructure（含运行时 + 循环编排 + 上下文装配 + 策略组件）
- Layer 2: Pluggable Components（模型/记忆/工具/MCP/技能/Hook）
- Layer 3: Composition（AgentBuilder 组装）

v2 将其重排为更“OS-kernel”式的 4 层：

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Developer API（开发者 API / 组装体验）                                │
│  - Builder / Fluent API / Config surface / sensible defaults                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Pluggable Components（可插拔组件）                                     │
│  - Strategies: Planner / Validator / Remediator / ContextStrategy              │
│  - Capabilities: ModelAdapter / Memory / Tools / Skills / Indexers / Hooks     │
└──────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Protocol Adapters（协议适配层）                                       │
│  - MCP / A2A / A2UI ...  (协议 = 如何发现/调用能力；不是能力本身)               │
└──────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Layer 0: Kernel（不可变内核 / 基础设施）                                        │
│  - Scheduling: IRunLoop, ILoopOrchestrator, IExecutionControl                  │
│  - Context+Resource: IContextManager, IResourceManager, IEventLog              │
│  - IO+Security: IToolGateway, ISecurityBoundary, IExtensionPoint               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 v2 的“内核最小集”

> **原则**：Kernel 只放“当 AI/Agent 技术快速变化时仍然必须稳定存在”的东西；  
> 任何“算法/策略/品味（opinionated strategy）”都应下放到组件层，Kernel 只保留结构骨架和控制面。

**Kernel 接口清单（v2）**：

| 类别 | Kernel 接口 | 角色类比 | 说明 |
|---|---|---|---|
| 调度与骨架 | `IRunLoop` | 调度器 | tick-based 状态机心跳 |
| 调度与骨架 | `ILoopOrchestrator` | 进程框架/调度框架 | 固化五层循环骨架（DARE 灵魂） |
| 长任务控制 | `IExecutionControl` | 中断/信号处理 | pause/resume/checkpoint/abort |
| 上下文工程 | `IContextManager` | 注意力/内存主管 | “决定什么进入上下文窗口”的总负责人 |
| 资源控制 | `IResourceManager` | MMU/预算中心 | token/cost/time/tool-call 预算统一模型 |
| 状态外化 | `IEventLog` | 文件系统/审计日志 | WORM 真理来源，可重放 |
| IO 边界 | `IToolGateway` | 系统调用接口 | 对外副作用唯一出口；不关心来源 |
| 安全边界 | `ISecurityBoundary` | ring0/ring3 边界 | Trust + Policy + Sandbox（组合式） |
| 扩展点 | `IExtensionPoint` | 内核模块接口 | lifecycle hooks / telemetry / policy taps |

> **注意**：这里是 9 个接口（而不是“凑到 10”）。  
> 类似 `ToolRegistry/SkillRegistry` 我们更倾向于作为 `IToolGateway` 的内部结构或 Layer 2 组件（实现细节可变），而非 Kernel contract。

### 1.2.1 Kernel 接口优先级（MVP：示例 Coding Agent）

> 本小节回答 “MVP 一个 coding agent 跑起来**必须**实现哪些 Kernel 接口，哪些可以先留白/做 stub”。  
> 这里的“MVP”指：能完成典型 coding 任务（读写文件、跑测试、修改代码），且对副作用有基本门禁与可追溯性。

| Kernel 接口 | 优先级 | MVP 最小实现（允许简化/留白） | 备注 |
|---|---:|---|---|
| `ILoopOrchestrator` | P0 | 跑通五层循环骨架（Session/Milestone/Plan/Execute/Tool），允许策略固定 | DARE 的“结构骨识”，不建议留白 |
| `IToolGateway` | P0 | 仅支持 native tool providers（文件/命令/版本控制）；能在 Envelope 约束下调用 | 协议层（MCP/A2A/A2UI）可先不做 |
| `ISecurityBoundary` | P0 | **Policy+Trust 必须有**；Sandbox 可先 stub（默认拒绝高风险或强制 HITL） | 避免“LLM 直接执行” |
| `IContextManager` | P0 | 支持 `assemble(PLAN/EXECUTE)`；`compress/retrieve/ensure_index/route` 可先 no-op 或返回空 | 责任在 Kernel，但实现可最小化 |
| `IEventLog` | P0 | append-only 事件记录（至少 task/milestone/plan/tool/verify）；hash chain 校验可后置 | 没有 log 难以 debug/审计 |
| `IResourceManager` | P1 | 先做粗粒度预算（tool calls/time）；token/cost 先不精确也可 | 预算超限应能触发中断或失败原因 |
| `IExecutionControl` | P1 | 先支持 `poll()` + `pause/resume()` 的最小流程；checkpoint 持久化可后置 | 长任务/HITL 的控制面 |
| `IRunLoop` | P1 | MVP 可把 `run()` 直接委托给 orchestrator；`tick()` 可先用固定步进或包装 run | tick 能力对可视化/调试很关键 |
| `IExtensionPoint` | P2 | 可先不实现或只做 no-op hooks registry | 指标/追踪/策略插桩后续再补 |

### 1.2.2 MVP（Coding Agent）还需要的“非 Kernel”组件

> Kernel 只提供基础设施；要拼出可用的 coding agent（示例），至少还需要这些 Layer 2 组件：

| 组件类别 | 最小需要 | 说明 |
|---|---|---|
| Model | `IModelAdapter` | 负责与 LLM 交互（可先 mock/deterministic） |
| Strategies | `IPlanner` + `IValidator` | 规划与验收（MVP 可用规则/简单 validator 起步） |
| Tools | File/Shell/Git providers | coding agent 的“手脚” |
| Remediation | `IRemediator` | 失败时生成 reflection，指导下一轮 Plan（可先 no-op） |
| Memory | 可选 | MVP 可先不做长期记忆；但建议保留接口位 |

### 1.3 “Framework 不做 Agent”在架构里的落点

DARE 的边界可以用一句话描述：

> **Kernel 提供**：运行、审计、安全、资源、上下文、IO 的基础设施；  
> **组件提供**：策略与能力；  
> **Developer API 提供**：把复杂性封装成易用组合的 DX。

因此 “coding agent” 只是 Layer 3 用默认组件拼出的一个 preset（示例），它不应反向决定 Kernel 的形状。

---

## 二、上下文工程统一模型

你给出的“上下文工程四层”非常适合作为 v2 的第一性原理：

```text
┌─────────────────────────────────────────────────────────────────┐
│                    上下文工程 (Context Engineering)              │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: 上下文调度 (Context Orchestration)                     │
│  Layer 3: 上下文组装 (Context Assembly)                          │
│  Layer 2: 上下文检索 (Context Retrieval)                         │
│  Layer 1: 上下文索引 (Context Indexing)                          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 v2 的统一观点：`IContextManager` 负责“全栈上下文工程”，但不必“全栈自研”

v2 里我们建议把这四层统一为一个“责任主体”：

> `IContextManager` 是“上下文工程的总负责人”，对外承诺：**决定什么进入上下文窗口，并给出可解释的理由/预算消耗**。  
> 但它不需要亲自实现所有层的细节，而是协调 Layer 2/1 的组件：
> - Layer 4（调度）：`IContextManager` 自己负责路由/compaction/handoff 的“决策逻辑”
> - Layer 3（组装）：通过 `IContextStrategy` 插件化实现 prompt/tool schemas/skills 注入
> - Layer 2（检索）：通过 `IMemory`/`IRetriever` 等组件实现
> - Layer 1（索引）：通常依赖外部工具/服务（例如 MCP Server / 本地索引器），`IContextManager` 只负责“何时触发/如何消费”

这能解决你提到的“现在架构没把四层清晰统一”的问题：**四层是一个体系，但实现可以分散；责任必须集中**。

### 2.2 v2 的映射（建议）

| 上下文工程层 | 责任主体（Kernel） | 主要实现来源（Layer 2 / 1） | 典型产物 |
|---:|---|---|---|
| L4 Orchestration | `IContextManager` + `IExecutionControl` | 多 Agent 路由器、compactor、handoff 策略 | `SessionSummary` / `MilestoneSummary` / `ContextPacket` |
| L3 Assembly | `IContextManager` | `IContextStrategy`, `IPromptStore`, tool schema minimizer | `AssembledPrompt` |
| L2 Retrieval | `IContextManager` | `IMemory`, `IRetriever`, graph-rag, agentic-search | `RetrievedFacts` / `MemoryItems` |
| L1 Indexing | `IContextManager`（触发/消费） | Indexer / AST / embedding / external servers | `IndexSnapshot` / `SymbolGraph` |

### 2.3 典型产物（Artifacts）：用途、存储与生命周期

> 这部分补全 “产物到底用来干什么/什么时候产生/谁来消费” 的语义。  
> 统一约定：**EventLog 是唯一真理来源**；其余产物要么是 view，要么是可从 log + 外部存储重建的派生物。

| 产物 | 产生时机 | 主要用途（谁消费） | 推荐存储位置 | Coding Agent MVP 场景 |
|---|---|---|---|---|
| `Event`（EventLog item） | 每个关键边界（plan/tool/verify/summary/approval） | 审计、回放、debug、复现（所有控制面/运维/开发者） | `IEventLog`（append-only） | 复盘“为什么改了这个文件/为什么失败” |
| `SessionSummary` | Session Loop 结束（或 checkpoint） | 下次会话快速载入历史（`IContextManager.open_session`） | EventLog +（可选）SessionStore | “继续上一次任务/基于上次结果再改” |
| `MilestoneSummary` | 单 milestone 成功/停止时 | 跨 milestone compaction、后续检索与解释（Context Orchestration） | EventLog | “前面做了哪些修改/已有证据是什么” |
| `Reflection` | Verify FAIL / 用户中断 / 策略失败时 | 指导下一轮 plan（Plan Loop 读 reflection） | EventLog（或与 milestone_ctx 绑定） | “测试失败原因→下一轮修复策略” |
| `AssembledPrompt` / `AssembledContext` | 每个 stage assemble 时 | LLM 输入；必须可解释 included items（planner/model adapter 消费） | 默认不持久化；建议写入 EventLog 的摘要/引用 | “Plan/Execute 阶段注入哪些文件/证据” |
| `RetrievedFacts` / `MemoryItems` | Retrieval 时 | 为 assembly 提供事实/上下文（ContextManager 消费） | `IMemory`（+ retrieval event 记录） | “从历史/知识库找相关 API/约定” |
| `IndexSnapshot` / `SymbolGraph` | Indexing 更新后 | 让 retrieval 更准更快（retriever/memory 消费） | 外部索引服务（可选） + 状态事件 | “代码符号级检索/跨仓库理解” |
| `ToolResult` / `Evidence` | Tool Loop 每次尝试 | Verify 与下一轮上下文（validator/context manager 消费） | EventLog（证据可引用外部 artifact） | “跑测试结果/命令输出作为验收证据” |
| `Checkpoint` | pause/HITL/显式 checkpoint 时 | 断点恢复与长任务承载（ExecutionControl 消费） | CheckpointStore（可文件化）+ EventLog 引用 | “HITL 审批后从断点继续” |
| `ContextPacket` | 多 agent / 多 session handoff | 上下文路由（`IContextManager.route` 消费） | EventLog + message bus（可选） | “把任务交给子 agent/把摘要交给 UI” |

> MVP 建议：先保证 `EventLog + SessionSummary + MilestoneSummary + Tool Evidence` 的闭环。  
> Retrieval/Indexing/ContextPacket 可以先做最小化或留白，但要把“接口位”和“事件记录”留下。

---

## 三、五层循环模型（v2 标准化）

v2 **保留** v1.3 的五层循环（这是 DARE 的差异化“骨识”），但将其标准化为 Kernel 的骨架（`ILoopOrchestrator`）：

1. **Session Loop**：跨对话持久化与用户边界（可恢复）
2. **Milestone Loop**：完成单个 Milestone（无用户输入）
3. **Plan Loop**：生成并验证计划（隔离失败计划，避免污染）
4. **Execute Loop**：LLM 驱动执行（遇到 Plan Tool/不可控情况回到外层）
5. **Tool Loop**：单工具调用的“目的达成”闭环（Envelope + DonePredicate）

### 3.1 完整循环架构图（v2：标注 Kernel 控制面）

> 目的：像 v1.3 一样，把“五层循环”画清楚，并明确 **新增 Kernel 接口** 在哪里发挥作用。

```text
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                           DARE v2 五层循环（标准化骨架）                          ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║  Cross-cutting Control Planes（每一层循环都必须显式检查/记录）                    ║
║    - IExecutionControl: poll/pause/resume/checkpoint (中断/恢复/HITL)             ║
║    - IResourceManager: check_limit/acquire/record (token/cost/time/tool-calls)   ║
║    - IEventLog: append(...) (WORM 真理来源，可重放)                                ║
║    - IExtensionPoint: emit(BEFORE/AFTER_*) (插桩/遥测/策略钩子)                    ║
║    - ISecurityBoundary: check_policy/verify_trust/execute_safe (门禁与隔离)       ║
║                                                                                   ║
║  L1: SESSION LOOP（用户交互边界 + 跨对话承载，可恢复）                             ║
║    输入：user_input + optional previous_session_summaries                          ║
║    关键调用：IContextManager.open_session() / compress()                            ║
║    产物：SessionSummary（供后续 Session 载入；也写入 EventLog）                    ║
║                                                                                   ║
║      for milestone in task.to_milestones():                                        ║
║        ┌───────────────────────────────────────────────────────────────────────┐  ║
║        │ L2: MILESTONE LOOP（无用户输入，目标闭环；可重试）                      │  ║
║        │  Observe: ctx = IContextManager.assemble(MILESTONE_OBSERVE, state)    │  ║
║        │          （可触发 retrieve/index；失败也应可追溯）                      │  ║
║        │                                                                       │  ║
║        │  ┌─────────────────────────────────────────────────────────────────┐ │  ║
║        │  │ L3: PLAN LOOP（隔离失败计划，生成 ValidatedPlan）                 │ │  ║
║        │  │  ctx = assemble(PLAN) → IPlanner.plan(ctx) → IValidator.validate │ │  ║
║        │  │  注意：失败 plan 不进入外层上下文（只记录 attempts + 反思）        │ │  ║
║        │  └───────────────┬─────────────────────────────────────────────────┘ │  ║
║        │                  ▼                                                    │  ║
║        │  Approve (HITL / Policy Checkpoint)                                   │  ║
║        │   - decision = ISecurityBoundary.check_policy(execute_plan, plan)     │  ║
║        │   - 若需要审批：IExecutionControl.pause() → 外部系统 resume()          │  ║
║        │                                                                       │  ║
║        │  ┌─────────────────────────────────────────────────────────────────┐ │  ║
║        │  │ L4: EXECUTE LOOP（LLM 对话驱动执行，允许动态调整）                  │ │  ║
║        │  │  ctx = assemble(EXECUTE)                                           │ │  ║
║        │  │  resp = IModelAdapter.generate/stream(ctx, tools=capabilities)     │ │  ║
║        │  │   - 遇到 tool call：进入 IToolGateway.invoke(...)                  │ │  ║
║        │  │   - 遇到 Plan Tool/不可控：跳回 L2 重新规划                         │ │  ║
║        │  └───────────────┬─────────────────────────────────────────────────┘ │  ║
║        │                  ▼                                                    │  ║
║        │  Verify: IValidator.verify_milestone(execute_result)                  │  ║
║        │   - PASS：产出 MilestoneSummary（写入 EventLog，供后续压缩/检索）      │  ║
║        │   - FAIL：IRemediator.remediate() → reflection → 回到 L3               │  ║
║        └───────────────────────────────────────────────────────────────────────┘  ║
║                                                                                   ║
║  L5: TOOL LOOP（WorkUnit：把“单次调用”变成“目的达成”）                             ║
║    输入：Envelope(allowed_capabilities + budget + done_predicate + risk)         ║
║    调用链：IToolGateway.invoke()                                                  ║
║      ├─ ISecurityBoundary.verify_trust(tool_name/params/envelope)                ║
║      ├─ ISecurityBoundary.check_policy(tool_call, risk)                          ║
║      └─ ISecurityBoundary.execute_safe(..., sandbox_spec)                        ║
║    产物：Evidence / ToolResult（写入 EventLog；可用于 Verify 与后续 Context）     ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
```

### 3.2 v2 的关键差异：控制面“显式化”

- **资源是否允许继续**：`IResourceManager.check_limit(...)`
- **是否收到中断/暂停/审批**：`IExecutionControl.poll()` / `ISecurityBoundary` 的审批流程
 - **可追溯性**：关键边界必须写 `IEventLog.append(...)`（否则无法 replay/审计）
 - **可插桩性**：关键阶段前后发 `IExtensionPoint.emit(...)`（便于 metrics/tracing/cost tracking）

### 3.3 关键接口在五层循环中的位置（速查）

| 循环层级 | 主要职责 | 必用 Kernel 接口 | 常见“组件层”协作者 |
|---:|---|---|---|
| Session | 用户交互边界、跨对话承载、生成 SessionSummary | `ILoopOrchestrator` / `IContextManager` / `IEventLog` / `IExecutionControl` |（可选）SessionStore / Memory |
| Milestone | 单目标闭环、重试、产出 MilestoneSummary | `ILoopOrchestrator` / `IContextManager` / `IResourceManager` / `IEventLog` | `IPlanner`/`IValidator`/`IRemediator` |
| Plan | 生成可执行计划并验证（隔离失败计划） | `IContextManager` / `IResourceManager` / `IEventLog` | `IPlanner` / `IValidator` |
| Execute | 对话驱动执行、触发工具调用、收集证据 | `IContextManager` / `IToolGateway` / `IEventLog` | `IModelAdapter` / Tools/Skills |
| Tool | WorkUnit：直到 done predicate 满足 | `IToolGateway` / `ISecurityBoundary` / `IResourceManager` / `IEventLog` | provider（native/MCP/A2A/A2UI） |

### 3.4 标准化伪码（强调控制面）

```python
async def run_task(task: Task, deps: Deps) -> RunResult:
    # Kernel control planes
    exec_ctl = kernel.execution_control()
    res_mgr = kernel.resource_manager()
    ctx_mgr = kernel.context_manager()
    log = kernel.event_log()
    io = kernel.tool_gateway()
    sec = kernel.security_boundary()

    await log.append("task.start", {"task": task})

    session = ctx_mgr.open_session(task)
    while session.has_more_user_turns():
        exec_ctl.poll_or_raise()
        res_mgr.check_limit(scope="session")

        milestone = session.next_milestone()
        result = await run_milestone(milestone)
        session.record(result.summary)

    await log.append("task.complete", {"success": session.success})
    return session.to_run_result()
```

> v1.3 的核心语义（Plan Loop 信息隔离、HITL 位置、WorkUnit 证据闭环）保持不变；  
> v2 的升级是把“预算/中断/上下文调度”变成所有循环的统一控制面，而不是散落在实现里。

### 3.5 Session 生命周期：DARE 如何承载“多轮会话”

> 这里的 `Session` 指 **一次用户输入触发的一次可恢复运行**（Session Loop 的一次迭代），而不是“某个具体 Agent 产品”的概念。  
> DARE 允许多个 Session 串联组成一个长对话/长任务：每次 Session 产出 `SessionSummary`，作为下一次 Session 的压缩输入。

**Session 生命周期（概念级）**：

```text
CREATED
  └─ open_session(task, previous_summaries)
       ↓
RUNNING
  ├─ (HITL / 外部中断) → PAUSED  ── resume(checkpoint_id) ──┐
  └─ (完成/取消/预算超限) → COMPLETED/ABORTED               │
                                                          │
ARCHIVED  <────────────────────────────────────────────────┘
  - EventLog 保留完整事件链
  - SessionSummary 用于后续 Session 的快速载入
```

**谁负责什么？（Session vs ContextManager）**

- `ILoopOrchestrator` 负责 **生命周期推进**：何时创建/运行/暂停/结束一个 Session（结构骨架）。
- `IExecutionControl` 负责 **暂停/恢复/Checkpoint 控制面**：HITL、超时、外部信号等。
- `IContextManager` 负责 **把 Session 状态投影成“可用的上下文窗口输入”**：装配/压缩/检索/路由。
  - 它不是“Session 本体”的 owner，而是 Session 的上下文工程主管（view builder）。
- `IEventLog` 负责 **真理来源**：Session 的可重放历史；`SessionSummary` 是派生压缩物。

换句话说：Session 是“生命周期容器”，ContextManager 是“把容器里的状态变成 prompt 的工程系统”。

### 3.6 多 Session Context 加载管理（TODO：v2 必须设计清楚）

你们提出的 TODO 很关键：**当用户说“继续上次/继续上周/参考另一个任务”时，加载哪些历史 Session？**

建议把它当作 `IContextManager.open_session()` 的一个显式子流程，并遵守预算：

1. **候选集**：从 SessionStore（或 EventLog 索引）列出历史 SessionSummary（按 recency/标签/项目等）。
2. **选择策略**：`MultiSessionSelectionPolicy`（可插拔）在预算内选择要载入的 summaries：
   - recency-first（最近 N 次）
   - query-based（用用户输入检索相关 sessions）
   - pinned（用户 pin 的长期上下文）
3. **合并与压缩**：把选中的多个 summary 进一步 compaction 成“本次 session 的可用历史基座”。
4. **可解释性**：记录 “加载了哪些 session/为什么加载/消耗了多少预算” 到 EventLog（否则难以 debug）。

> v2.0 MVP 可以先做 `recency-first`：只加载 `previous_session_summary` + 最近 1~N 个 `SessionSummary`。  
> 但必须把接口位与事件记录打通，为后续检索式多 session 做铺垫。

---

## 四、核心接口定义（v2）

> 说明：以下是 **规范性接口草案**（Spec），不是当前代码实现的真实 API。  
> 我们先把“终稿评审级别的 contract”写清楚，再进入实现迭代。

### 4.1 Layer 0: Kernel（不可变）

#### 4.1.1 `IRunLoop`（状态机化心跳）

```python
from enum import Enum
from typing import Protocol

class RunLoopState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    PAUSED = "paused"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    ABORTED = "aborted"

class IRunLoop(Protocol):
    @property
    def state(self) -> RunLoopState: ...

    async def tick(self) -> "TickResult":
        """执行一个最小调度步，便于可视化/调试/中断。"""
        ...

    async def run(self, task: "Task") -> "RunResult":
        """驱动直到终止（内部不断 tick）。"""
        ...
```

#### 4.1.2 `ILoopOrchestrator`（五层循环骨架）

> **骨架不可替换，策略可替换**：DARE 的差异化在于“结构”，而不是某个 planner 算法。

```python
from typing import Protocol

class ILoopOrchestrator(Protocol):
    async def run_session_loop(self, task: "Task") -> "SessionResult": ...
    async def run_milestone_loop(self, milestone: "Milestone") -> "MilestoneResult": ...
    async def run_plan_loop(self, milestone: "Milestone") -> "ValidatedPlan": ...
    async def run_execute_loop(self, plan: "ValidatedPlan") -> "ExecuteResult": ...
    async def run_tool_loop(self, req: "ToolLoopRequest") -> "ToolLoopResult": ...
```

#### 4.1.3 `IExecutionControl`（中断/恢复/Checkpoint）

> v1.3 的 `ICheckpoint` 在 v2 被吸收为 `IExecutionControl` 的能力面；  
> 底层存储可作为 Layer 2 组件（CheckpointStore），但对上暴露统一控制接口。

```python
from typing import Protocol, Optional

class ExecutionSignal(Enum):
    NONE = "none"
    PAUSE_REQUESTED = "pause_requested"
    CANCEL_REQUESTED = "cancel_requested"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"

class IExecutionControl(Protocol):
    def poll(self) -> ExecutionSignal:
        """查询当前控制信号（来自预算超限、HITL、外部中断等）。"""
        ...

    def poll_or_raise(self) -> None:
        """便捷接口：若需要暂停/取消则抛出标准异常，由 Orchestrator 处理。"""
        ...

    async def pause(self, reason: str) -> str:
        """进入 PAUSED，并创建 checkpoint；返回 checkpoint_id。"""
        ...

    async def resume(self, checkpoint_id: str) -> None:
        """从 checkpoint 恢复运行。"""
        ...

    async def checkpoint(self, label: str, payload: dict) -> str:
        """显式创建 checkpoint（便于开发者/系统 hook 插入）。"""
        ...
```

#### 4.1.4 `IContextManager`（上下文工程总负责人）

> **关键定义**：`IContextManager` 负责上下文工程四层（Orchestration/Assembly/Retrieval/Indexing）的“决策与协调”。  
> 具体实现来自组件层：memory/retriever/indexer/prompt store/context strategies 等。

```python
from typing import Protocol, Sequence

class ContextStage(Enum):
    SESSION_OBSERVE = "session_observe"
    MILESTONE_OBSERVE = "milestone_observe"
    PLAN = "plan"
    EXECUTE = "execute"
    TOOL = "tool"
    VERIFY = "verify"

class IContextManager(Protocol):
    def open_session(self, task: "Task") -> "SessionContext": ...

    async def assemble(self, stage: ContextStage, state: "RuntimeStateView") -> "AssembledContext":
        """
        组装当前阶段 prompt（含系统指令、工具 schema、相关记忆、摘要等）。
        要求：可解释（why included）、可计费（token/cost attribution）。
        """
        ...

    async def retrieve(self, query: str, *, budget: "Budget") -> "RetrievedContext":
        """上下文检索（L2 retrieval）：调用 memory/retriever 组件。"""
        ...

    async def ensure_index(self, scope: str) -> "IndexStatus":
        """上下文索引（L1 indexing）：触发/检查外部索引就绪度（可选）。"""
        ...

    async def compress(self, context: "AssembledContext", *, budget: "Budget") -> "AssembledContext":
        """跨窗口压缩/summary（L4 orchestration 的关键动作）。"""
        ...

    async def route(self, packet: "ContextPacket", target: str) -> None:
        """多 agent / 多进程场景的上下文路由（可选能力）。"""
        ...
```

#### 4.1.5 `IResourceManager`（统一预算模型）

```python
from typing import Protocol

class ResourceType(Enum):
    TOKENS = "tokens"
    COST = "cost"
    TIME_SECONDS = "time_seconds"
    TOOL_CALLS = "tool_calls"

class IResourceManager(Protocol):
    def get_budget(self, scope: str) -> "Budget": ...

    def acquire(self, resource: ResourceType, amount: float, *, scope: str) -> None:
        """申请资源额度（失败抛出 ResourceExhausted）。"""
        ...

    def record(self, resource: ResourceType, amount: float, *, scope: str) -> None:
        """记录消耗（用于审计与策略反馈）。"""
        ...

    def check_limit(self, *, scope: str) -> None:
        """若超限抛出 ResourceExhausted。"""
        ...
```

#### 4.1.6 `IEventLog`（WORM 真理来源）

```python
from typing import Protocol, Optional, Sequence

class IEventLog(Protocol):
    async def append(self, event_type: str, payload: dict) -> str: ...
    async def query(self, *, filter: Optional[dict] = None, limit: int = 100) -> Sequence["Event"]: ...
    async def replay(self, *, from_event_id: str) -> "RuntimeSnapshot": ...
    async def verify_chain(self) -> bool: ...
```

#### 4.1.7 `IToolGateway`（系统调用接口：统一执行入口）

> 这是你提到的“抽象与实现分离”的落点：  
> **Gateway 只定义如何调用能力（capability），不定义能力来自哪里**。

```python
from typing import Protocol, Sequence, Any

class CapabilityType(Enum):
    TOOL = "tool"      # 工具能力（本地/远程）
    AGENT = "agent"    # A2A peer（可被当成工具调用）
    UI = "ui"          # A2UI 渲染/输入请求（可被当成工具调用）

class IToolGateway(Protocol):
    async def list_capabilities(self) -> Sequence["CapabilityDescriptor"]: ...
    async def invoke(self, capability_id: str, params: dict, *, envelope: "Envelope") -> Any: ...
    def register_provider(self, provider: "ICapabilityProvider") -> None: ...
```

> **与 v1.3 的 `IToolRuntime` 的区别（语义层面）**：  
> - `IToolRuntime` 更像“工具执行总线（实现导向）”：找工具、注入 ctx、区分 Plan Tool、进入 Tool Loop。  
> - `IToolGateway` 更像“系统调用边界（边界导向）”：对外副作用的唯一出口 + 统一能力模型（capability），至于来自 native toolkit、MCP、A2A，都由 provider/adapter 解决。  
> 两者功能可高度重叠，但 v2 更强调 **边界清晰与协议无关**。

#### 4.1.8 `ISecurityBoundary`（Trust + Policy + Sandbox，组合式）

> v2 不建议把 trust/policy/sandbox 强行揉成一个巨石实现；  
> 建议以 `ISecurityBoundary` 作为 Kernel contract，对内由三个子模块组合：
> - Trust：验证 LLM 输出/外部输入的可信度与派生安全字段（延续 v1.3 TrustBoundary）
> - Policy：权限/风险/HITL（延续 v1.3 PolicyEngine）
> - Sandbox：对副作用执行提供隔离（可选，先给最小可用实现）

```python
from typing import Protocol, Any

class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVE_REQUIRED = "approve_required"

class ISecurityBoundary(Protocol):
    async def verify_trust(self, *, input: dict, context: dict) -> "TrustedInput":
        """派生可信字段：不信任 LLM 自报的危险等级/路径/权限等。"""
        ...

    async def check_policy(self, *, action: str, resource: str, context: dict) -> PolicyDecision:
        """风险识别与 HITL 触发。"""
        ...

    async def execute_safe(self, *, action: str, fn: "Callable[[], Any]", sandbox: "SandboxSpec") -> Any:
        """在沙箱/隔离策略下执行副作用（可先做最小实现）。"""
        ...
```

#### 4.1.9 `IExtensionPoint`（系统级扩展点）

```python
from typing import Protocol, Callable, Any

class HookPhase(Enum):
    BEFORE_PLAN = "before_plan"
    AFTER_PLAN = "after_plan"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_VERIFY = "before_verify"
    AFTER_VERIFY = "after_verify"

class IExtensionPoint(Protocol):
    def register_hook(self, phase: HookPhase, callback: Callable[[dict], Any]) -> None: ...
    async def emit(self, phase: HookPhase, payload: dict) -> None: ...
```

---

### 4.2 Layer 1: Protocol Adapters（协议适配层）

> 你最后那张图的启发点非常关键：  
> **Protocol Adapter 负责“把协议世界翻译成 Kernel 世界”**（canonical types），而不是把协议直接渗透进 Kernel。

```python
from typing import Protocol, Sequence, Any

class IProtocolAdapter(Protocol):
    @property
    def protocol_name(self) -> str: ...

    async def connect(self, endpoint: str, config: dict) -> None: ...
    async def disconnect(self) -> None: ...

    async def discover(self) -> Sequence["CapabilityDescriptor"]:
        """发现对端能力（工具/agent/ui），并翻译成 canonical descriptors。"""
        ...

    async def invoke(self, capability_id: str, params: dict, *, timeout: float | None = None) -> Any: ...
```

建议的适配器划分：
- `MCPAdapter`：发现 MCP tools → `CapabilityType.TOOL`
- `A2AAdapter`：把 peer agent 的能力 → `CapabilityType.AGENT`
- `A2UIAdapter`：把 UI 能力（render/input/progress）→ `CapabilityType.UI`

---

### 4.3 Layer 2: Pluggable Components（组件层）

#### 4.3.1 策略组件（Strategies）

```python
class IPlanner(Protocol):
    async def plan(self, ctx: "AssembledContext") -> "ProposedPlan": ...

class IValidator(Protocol):
    async def validate_plan(self, plan: "ProposedPlan", ctx: dict) -> "ValidatedPlan": ...
    async def verify_milestone(self, result: "ExecuteResult", ctx: dict) -> "VerifyResult": ...

class IRemediator(Protocol):
    async def remediate(self, verify_result: "VerifyResult", ctx: dict) -> str: ...

class IContextStrategy(Protocol):
    async def build_prompt(self, assembled: "AssembledContext") -> "Prompt": ...
```

#### 4.3.2 能力组件（Capabilities）

```python
class IModelAdapter(Protocol): ...
class IMemory(Protocol): ...
class ICapabilityProvider(Protocol):
    async def list(self) -> list["CapabilityDescriptor"]: ...
    async def invoke(self, capability_id: str, params: dict) -> object: ...
```

---

### 4.4 Layer 3: Developer API（开发者 API）

> Layer 3 的目标是“屏蔽复杂性”，让开发者用最少概念完成组装。

```python
agent = (
    AgentBuilder()
      .with_kernel_defaults()
      .with_model(ClaudeAdapter(...))
      .with_tools(FileSystemTools(), ShellTools())
      .with_protocol(MCPAdapter(...))   # 可选
      .with_memory(VectorMemory(...))   # 可选
      .with_budget(tokens=..., cost=...)# 显式预算
      .build()
)
```

### 4.3 扩展性与插件系统 (Layer 2)

DARE v2 采用基于 Python entrypoints 的标准化插件发现机制。

#### 4.3.1 Plugin Entrypoint Groups (v2)

| 类型 | Entrypoint Group Name | 策略 |
|---|---|---|
| 工具 | `dare_framework.v2.tools` | Multi-load |
| 模型适配器 | `dare_framework.v2.model_adapters` | Single-select |
| 规划器 | `dare_framework.v2.planners` | Single-select |
| 验收器 | `dare_framework.v2.validators` | Multi-load (ordered) |
| 反思器 | `dare_framework.v2.remediators` | Single-select |
| 协议适配器 | `dare_framework.v2.protocol_adapters` | Multi-load |
| 钩子 | `dare_framework.v2.hooks` | Multi-load |
| 配置管理器 | (N/A) | ConfigManager (non-plugin) |

#### 4.3.2 插件加载与配置过滤

- **Manager 驱动**：每个类别由专门的 `IComponentManager` 接口负责加载。默认实现为 No-Op。
- **配置过滤**：`AgentBuilder` 会根据 `Config` 中的 `components.<type>.disabled` 列表过滤已加载的插件。
- **显式覆盖**：Builder 上的 `.with_*()` 方法具有最高优先级，优于插件发现。

---

## 五、核心数据结构 (v2)

> 目标：把 v1.3 的核心数据模型延续下来，同时为 v2 的 Protocol/Context/Control 面补齐 canonical types。

### 5.1 Capability（统一能力模型）

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CapabilityDescriptor:
    id: str
    type: CapabilityType
    name: str
    description: str
    input_schema: dict
    output_schema: dict | None = None
    metadata: dict | None = None
```

### 5.2 Envelope（执行边界）

> Envelope 继续作为 Tool Loop 的“可控执行边界”：允许哪些能力、预算是多少、DonePredicate 是什么。
>
> v2.1 约束：
> - `Envelope` **不承载** 本次调用的 `capability_id/params`（避免混淆边界与 payload）。
> - `risk_level` 视为**可信字段**：必须由 validator/runtime 从 registry 与策略派生，不能直接信任模型/规划器填写。

```python
@dataclass(frozen=True)
class Envelope:
    allowed_capability_ids: list[str]
    budget: "Budget"
    done_predicate: "DonePredicate"
    risk_level: "RiskLevel"
```

### 5.3 ToolLoopRequest（Tool Loop 调用请求）

> Tool Loop 输入分为两部分：
> - `Envelope`：执行边界（允许范围/预算/done/risk）
> - `ToolLoopRequest`：本次调用 payload（capability + params）

```python
@dataclass(frozen=True)
class ToolLoopRequest:
    capability_id: str
    params: dict
    envelope: "Envelope"
```

### 5.4 Budget（统一预算）

```python
@dataclass(frozen=True)
class Budget:
    max_tokens: int | None = None
    max_cost: float | None = None
    max_time_seconds: int | None = None
    max_tool_calls: int | None = None
```

### 5.5 Checkpoint（由 ExecutionControl 管理）

```python
@dataclass(frozen=True)
class Checkpoint:
    id: str
    created_at: float
    event_id: str              # 与 EventLog 对齐（可重放）
    snapshot_ref: str | None   # 可选：指向快照存储
    note: str | None = None
```

### 5.6 ContextPacket（跨窗口/跨 Agent 传递）

```python
@dataclass(frozen=True)
class ContextPacket:
    id: str
    source: str
    target: str
    summary: str
    attachments: list[str]     # refs: event ids / artifact ids / urls
    budget_attribution: dict   # token/cost attribution
```

---

## 六、执行流程详解（v2）

### 6.1 Plan Loop 信息隔离（保持 v1.3 核心）

```python
async def plan_loop(milestone):
    attempts = []
    for i in range(plan_budget.max_attempts):
        exec_ctl.poll_or_raise()
        res_mgr.check_limit(scope="plan")

        assembled = await ctx_mgr.assemble(ContextStage.PLAN, state_view())
        proposed = await planner.plan(assembled)
        validated = await validator.validate_plan(proposed, ctx=state_view())

        if validated.success:
            return validated
        attempts.append(validated.errors)

    raise PlanGenerationFailed(attempts=attempts)
```

### 6.2 HITL 的位置（在 Plan 与 Execute 之间）

```python
validated = await plan_loop(milestone)

decision = await sec.check_policy(action="execute_plan", resource=validated.summary, context=state_view())
if decision == PolicyDecision.APPROVE_REQUIRED:
    checkpoint_id = await exec_ctl.pause("hitl_approval_required")
    # 外部系统恢复
    await exec_ctl.resume(checkpoint_id)
```

### 6.3 Tool Loop：把“单次工具调用”变成“目的达成”

```python
async def tool_loop(req: ToolLoopRequest):
    max_calls = req.envelope.budget.max_tool_calls or 1
    for _ in range(max_calls):
        exec_ctl.poll_or_raise()
        res_mgr.check_limit(scope="tool")

        # 所有副作用都经由 IToolGateway（系统调用边界）
        result = await io.invoke(req.capability_id, req.params, envelope=req.envelope)

        # 证据与 done predicate 决定是否完成
        if req.envelope.done_predicate.is_satisfied(result.evidence):
            return result

        # 下一次尝试如何调整 params/envelope 由具体实现决定（可先不做，或交由 remediator/skill 派生）。
```

---

## 七、组件实现清单（建议）

> 这部分是“建议的默认实现”，不是 v2 Kernel contract。

### 7.1 Kernel 默认实现（最小可运行）
- `DefaultRunLoop`：tick-based 状态机
- `DefaultLoopOrchestrator`：五层循环骨架实现
- `DefaultExecutionControl`：pause/resume/checkpoint 的最小实现（可先文件化）
- `LocalEventLog`：append-only + hash chain
- `DefaultToolGateway`：聚合多个 provider（native + protocol）
- `DefaultSecurityBoundary`：trust/policy/sandbox 组合式实现（sandbox 可先 stub）
- `DefaultExtensionPoint`：hooks 管理器

### 7.2 组件层（Layer 2）建议默认集
- Strategies: `LLMPlanner`, `SchemaValidator`, `CompositeValidator`, `NoOpRemediator`, `SlidingWindowContextStrategy`
- Capabilities: `FileSystemTools`, `ShellTools`, `GitTools`, `InMemoryMemory`, `VectorMemory`
- Protocol: `MCPAdapter`（优先），A2A/A2UI 可暂不实现

---

## 八、使用示例（framework 视角）

### 8.1 作为框架：只提供可组合的 lego

```python
framework = (
  DARE()
    .with_kernel_defaults()
    .with_components(default_components())
)

coding_agent = (
  framework.builder()
    .with_model(ClaudeAdapter(...))
    .with_tools(FileSystemTools(), ShellTools(), GitTools())
    .with_budget(tokens=120_000, cost=5.0)
    .build()
)
```

### 8.2 作为生态底座：MCP 只是能力来源之一

```python
agent = (
  framework.builder()
    .with_protocol(MCPAdapter(endpoint="stdio://..."))
    .build()
)
```

---

## 九、设计决策记录（v2）

### 决策 1：为什么要 Kernel 化？
- AI/Agent 生态变化快：Kernel 必须稳定、策略必须可替换
- Framework 关注底层控制面：调度、资源、IO、安全、审计

### 决策 2：为什么 `IContextManager` 要成为 Kernel？
- “什么进入上下文窗口”是 AI-native 的核心资源分配问题
- 它跨越五层循环，是系统级控制面，不能散落在实现里

### 决策 3：为什么引入 `Layer 1 Protocol Adapters`？
- 协议是“通信标准”，不是“能力实现”
- 让 Kernel 协议无关，避免 MCP/A2A/A2UI 绑死内核

### 决策 4：为什么 `ISecurityBoundary` 统一但保留 trust/policy 子模块？
- 统一边界可以简化调用方心智
- 但 trust/policy/sandbox 的变化速度不同，必须组合式演进避免巨石接口

---

## 附录：v1.3 → v2 术语对照与迁移点

### A.1 主要接口迁移（概念级）

| v1.3 | v2 | 说明 |
|---|---|---|
| `IRuntime` | `IRunLoop` + `ILoopOrchestrator` | 状态机心跳 vs 五层循环骨架 |
| `ICheckpoint` | `IExecutionControl` | Checkpoint 成为控制面能力 |
| `IContextAssembler` | `IContextManager`（+ `IContextStrategy`） | 上下文工程统一责任主体 |
| `IToolRuntime` | `IToolGateway` | 从“执行总线”升级为“系统调用边界” |
| `TrustBoundary` + `IPolicyEngine` | `ISecurityBoundary`（组合式） | trust/policy/sandbox 统一边界 |
| `IMCPClient` | `Layer 1 MCPAdapter`（或 provider） | 协议适配与能力来源分离 |

### A.2 遗留问题（需要在 v2 迭代中定稿）
1. `CapabilityType.AGENT/UI` 是否纳入 v2.0 首发，或作为后续扩展？
2. `IContextManager.ensure_index()` 的责任边界：仅检查/触发，还是包含增量更新策略？
3. `SandboxSpec` 的最小可用定义：先以“高风险操作必须 HITL + 默认拒绝”替代真正 sandbox，是否可接受？
4. 多 Session Context 加载策略：`previous_session_summary` 之外，如何选择/压缩/解释性记录历史 SessionSummary？
5. 事件模型定稿：Event 类型枚举、payload schema、correlation ids（task/session/milestone/tool），以及 replay 的最小要求。
6. Envelope/DonePredicate 的来源：由 `Skill`/`Tool` 定义、还是由 `IValidator.validate_plan` 派生，二者如何组合与审计？
