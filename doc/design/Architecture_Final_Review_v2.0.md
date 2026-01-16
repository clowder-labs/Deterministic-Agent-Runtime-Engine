# DARE Framework 架构终稿评审 v2.0（草案）：内核化与上下文工程

> **定位声明（请先读）**：DARE 是 **framework**，不交付“某个具体 Agent 产品”。  
> DARE 交付的是一套 **Kernel + 组件体系 + 开发者 API**，开发者用它来组装不同类型的 Agent Runtime。  
> `examples/` 里的 coding agent 只是一个示例组合（composition），不是框架本体。

> **v2.0 相对 v1.3 的核心变更**：
> 1. **架构内核化**：引入 `Layer 0: Kernel`（不可变基础设施），把“策略/算法”整体下放为可插拔组件。
> 2. **上下文工程优先**：用 `IContextManager + IResourceManager` 显式管理“什么进入上下文窗口”（注意力资源）。
> 3. **协议与实现分离**：引入 `Layer 1.5: Protocol Adapters`（MCP/A2A/A2UI），Kernel 协议无关。
> 4. **长任务原生支持**：将 Checkpoint/暂停/恢复收敛到 `IExecutionControl`（中断控制面）。
> 5. **安全边界升级**：以 `ISecurityBoundary` 统一表达 **Trust + Policy + Sandbox**，但保留 trust/policy 子模块以避免“巨石接口”。

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
│ Layer 1.5: Protocol Adapters（协议适配层）                                     │
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
> 但它不需要亲自实现所有层的细节，而是协调 Layer 2/1.5 的组件：
> - Layer 4（调度）：`IContextManager` 自己负责路由/compaction/handoff 的“决策逻辑”
> - Layer 3（组装）：通过 `IContextStrategy` 插件化实现 prompt/tool schemas/skills 注入
> - Layer 2（检索）：通过 `IMemory`/`IRetriever` 等组件实现
> - Layer 1（索引）：通常依赖外部工具/服务（例如 MCP Server / 本地索引器），`IContextManager` 只负责“何时触发/如何消费”

这能解决你提到的“现在架构没把四层清晰统一”的问题：**四层是一个体系，但实现可以分散；责任必须集中**。

### 2.2 v2 的映射（建议）

| 上下文工程层 | 责任主体（Kernel） | 主要实现来源（Layer 2 / 1.5） | 典型产物 |
|---:|---|---|---|
| L4 Orchestration | `IContextManager` + `IExecutionControl` | 多 Agent 路由器、compactor、handoff 策略 | `SessionSummary` / `MilestoneSummary` / `ContextPacket` |
| L3 Assembly | `IContextManager` | `IContextStrategy`, `IPromptStore`, tool schema minimizer | `AssembledPrompt` |
| L2 Retrieval | `IContextManager` | `IMemory`, `IRetriever`, graph-rag, agentic-search | `RetrievedFacts` / `MemoryItems` |
| L1 Indexing | `IContextManager`（触发/消费） | Indexer / AST / embedding / external servers | `IndexSnapshot` / `SymbolGraph` |

---

## 三、五层循环模型（v2 标准化）

v2 **保留** v1.3 的五层循环（这是 DARE 的差异化“骨识”），但将其标准化为 Kernel 的骨架（`ILoopOrchestrator`）：

1. **Session Loop**：跨对话持久化与用户边界（可恢复）
2. **Milestone Loop**：完成单个 Milestone（无用户输入）
3. **Plan Loop**：生成并验证计划（隔离失败计划，避免污染）
4. **Execute Loop**：LLM 驱动执行（遇到 Plan Tool/不可控情况回到外层）
5. **Tool Loop**：单工具调用的“目的达成”闭环（Envelope + DonePredicate）

### 3.1 v2 的关键差异：每一层都必须显式检查两件事

- **资源是否允许继续**：`IResourceManager.check_limit(...)`
- **是否收到中断/暂停/审批**：`IExecutionControl.poll()` / `ISecurityBoundary` 的审批流程

### 3.2 标准化伪码（强调控制面）

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
    async def run_tool_loop(self, envelope: "Envelope") -> "ToolLoopResult": ...
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

### 4.2 Layer 1.5: Protocol Adapters（协议适配层）

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

---

## 五、核心数据结构（v2）

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

```python
@dataclass(frozen=True)
class Envelope:
    allowed_capability_ids: list[str]
    budget: "Budget"
    done_predicate: "DonePredicate"
    risk_level: "RiskLevel"
```

### 5.3 Budget（统一预算）

```python
@dataclass(frozen=True)
class Budget:
    max_tokens: int | None = None
    max_cost: float | None = None
    max_time_seconds: int | None = None
    max_tool_calls: int | None = None
```

### 5.4 Checkpoint（由 ExecutionControl 管理）

```python
@dataclass(frozen=True)
class Checkpoint:
    id: str
    created_at: float
    event_id: str              # 与 EventLog 对齐（可重放）
    snapshot_ref: str | None   # 可选：指向快照存储
    note: str | None = None
```

### 5.5 ContextPacket（跨窗口/跨 Agent 传递）

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
async def tool_loop(envelope: Envelope):
    while True:
        exec_ctl.poll_or_raise()
        res_mgr.check_limit(scope="tool")

        # 所有副作用都经由 IToolGateway（系统调用边界）
        result = await io.invoke(envelope.current_capability_id, envelope.params, envelope=envelope)

        # 证据与 done predicate 决定是否完成
        if envelope.done_predicate.is_satisfied(result.evidence):
            return result

        envelope = envelope.next_attempt(result)
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

### 决策 3：为什么引入 `Layer 1.5 Protocol Adapters`？
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
| `IMCPClient` | `Layer 1.5 MCPAdapter`（或 provider） | 协议适配与能力来源分离 |

### A.2 遗留问题（需要在 v2 迭代中定稿）
1. `CapabilityType.AGENT/UI` 是否纳入 v2.0 首发，或作为后续扩展？
2. `IContextManager.ensure_index()` 的责任边界：仅检查/触发，还是包含增量更新策略？
3. `SandboxSpec` 的最小可用定义：先以“高风险操作必须 HITL + 默认拒绝”替代真正 sandbox，是否可接受？

