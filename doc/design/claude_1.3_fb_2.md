# DARE Framework 架构设计文档

> **作者**: Claude (Anthropic)  
> **日期**: 2025-01-15  
> **版本**: v1.0 - 架构讨论稿

---

## 一、第一性原理：从 OS 内核到 Agent Kernel

### 1.1 为什么要对标 OS？

Agent Framework 和操作系统面临的**本质问题相同**：

```
┌─────────────────────────────────────────────────────────────────┐
│  共同挑战：如何在不可预测的环境中，安全、可靠地执行任务？         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   OS 面对：                      Agent 面对：                   │
│   • 不可预测的用户程序            • 不可预测的 LLM 输出          │
│   • 有限的硬件资源                • 有限的 Token/成本预算        │
│   • 需要隔离和保护                • 需要信任边界和验证           │
│   • 需要持久化和恢复              • 需要 Checkpoint 和 Resume    │
│   • 需要与外设通信                • 需要与工具/其他Agent通信     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 OS 内核管理了什么？

| OS 内核职责 | 具体功能 | Agent 对应需求 |
|------------|---------|---------------|
| **进程调度** | 决定谁在运行、运行多久 | Agent 循环调度、状态机转换 |
| **内存管理** | 分配、回收、保护内存 | Context Window 管理、Token 预算 |
| **I/O 抽象** | 统一的设备访问接口 | 统一的工具调用接口 |
| **中断处理** | 响应外部事件、保存/恢复状态 | HITL、超时、暂停/恢复 |
| **安全边界** | 用户态/内核态隔离、权限检查 | 信任验证、沙箱执行 |
| **文件系统** | 持久化存储抽象 | 事件日志、状态持久化 |
| **系统调用** | 用户程序与内核的唯一接口 | LLM 与外部世界的唯一接口 |

### 1.3 核心设计原则

```
┌─────────────────────────────────────────────────────────────────┐
│                     DARE Kernel 设计原则                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 最小化 Core：只放"不可或缺"的，其他都是插件                  │
│                                                                 │
│  2. 稳定性优先：Core 层接口应该在 AI 技术剧变时仍然稳定          │
│                                                                 │
│  3. 单一职责：每个 Core 接口只做一件事                           │
│                                                                 │
│  4. 显式依赖：组件间依赖清晰可见，无隐式耦合                     │
│                                                                 │
│  5. 可观测性：一切皆可记录、可追溯、可重放                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、分层架构总览

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        DARE Framework 分层架构                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  ║
║  ┃ Layer 3: Developer API（开发者接口层）                                  ┃  ║
║  ┃                                                                         ┃  ║
║  ┃   AgentBuilder / Fluent API / Decorators / Configuration               ┃  ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  ║
║                                         │                                     ║
║                                         ▼                                     ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  ║
║  ┃ Layer 2: Pluggable Components（可插拔组件层）                           ┃  ║
║  ┃                                                                         ┃  ║
║  ┃   Model Adapters / Memory / Tools / Skills / Hooks / Validators        ┃  ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  ║
║                                         │                                     ║
║                                         ▼                                     ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  ║
║  ┃ Layer 1.5: Protocol Adapters（协议适配层）                              ┃  ║
║  ┃                                                                         ┃  ║
║  ┃   MCP (Tool Protocol) / A2A (Agent Protocol) / A2UI (UI Protocol)      ┃  ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  ║
║                                         │                                     ║
║                                         ▼                                     ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  ║
║  ┃ Layer 1: Kernel（内核层）                                               ┃  ║
║  ┃                                                                         ┃  ║
║  ┃   IRunLoop / IEventLog / IToolGateway / ISecurityBoundary /            ┃  ║
║  ┃   IResourceManager / IExecutionControl / IExtensionPoint               ┃  ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## 三、Layer 1: Kernel（内核层）详细设计

### 3.1 核心接口清单

| 接口 | OS 对应 | 职责 | 必要性 |
|------|--------|------|--------|
| `IRunLoop` | 进程调度器 | Agent 执行循环、状态机 | 🔴 必须 |
| `IEventLog` | 文件系统/审计日志 | WORM 事件记录、状态外化 | 🔴 必须 |
| `IToolGateway` | 系统调用接口 | 工具执行的唯一入口 | 🔴 必须 |
| `ISecurityBoundary` | 安全边界/MMU | 信任验证 + 沙箱隔离 | 🔴 必须 |
| `IResourceManager` | 内存管理器 | Token/成本/时间预算 | 🔴 必须 |
| `IExecutionControl` | 中断处理器 | 暂停/恢复/Checkpoint | 🔴 必须 |
| `IExtensionPoint` | 内核模块接口 | 生命周期钩子 | 🟡 重要 |

### 3.2 各接口详细设计

#### 3.2.1 IRunLoop（执行调度器）

```python
"""
OS 对应：进程调度器 (Process Scheduler)
- 决定下一步执行什么
- 管理状态转换
- 驱动整个 Agent 生命周期
"""

class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    REMEDIATING = "remediating"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class IRunLoop(Protocol):
    """Agent 执行循环 - 框架的心跳"""
    
    @property
    def state(self) -> AgentState:
        """当前状态"""
        ...
    
    async def tick(self) -> TickResult:
        """
        执行一个循环步骤
        返回: 下一步动作或终止信号
        """
        ...
    
    async def run(self, task: Task) -> AgentResult:
        """
        运行完整的 Agent 循环直到完成
        内部调用 tick() 直到终止
        """
        ...
    
    def transition(self, new_state: AgentState) -> None:
        """显式状态转换"""
        ...
```

**设计要点**：
- 状态机化：所有状态转换显式、可追踪
- tick-based：便于中断、调试、可视化
- 不包含具体策略：如何规划、如何验证都由插件决定

---

#### 3.2.2 IEventLog（事件日志）

```python
"""
OS 对应：文件系统 + 审计日志
- WORM (Write-Once-Read-Many) 语义
- Agent 的"黑匣子"
- 支持状态重放和调试
"""

class EventType(Enum):
    TASK_STARTED = "task_started"
    PLAN_GENERATED = "plan_generated"
    STEP_STARTED = "step_started"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    VALIDATION_RESULT = "validation_result"
    HUMAN_INPUT = "human_input"
    STATE_CHANGED = "state_changed"
    CHECKPOINT_CREATED = "checkpoint_created"
    ERROR_OCCURRED = "error_occurred"
    TASK_COMPLETED = "task_completed"

@dataclass(frozen=True)
class Event:
    id: str                     # 唯一事件ID
    type: EventType
    timestamp: datetime
    payload: dict
    parent_id: Optional[str]    # 因果链
    hash: str                   # 完整性校验

class IEventLog(Protocol):
    """WORM 事件日志 - 不可变的真理来源"""
    
    def append(self, event_type: EventType, payload: dict) -> Event:
        """
        追加事件（不可修改已有事件）
        自动计算 hash chain 保证完整性
        """
        ...
    
    def get(self, event_id: str) -> Optional[Event]:
        """获取单个事件"""
        ...
    
    def query(
        self,
        event_types: Optional[List[EventType]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """查询事件"""
        ...
    
    def replay(
        self,
        from_event: Optional[str] = None,
        to_event: Optional[str] = None
    ) -> Iterator[Event]:
        """重放事件流（用于调试/恢复）"""
        ...
    
    def verify_integrity(self) -> bool:
        """验证 hash chain 完整性"""
        ...
```

**设计要点**：
- WORM 语义：写入后不可修改，保证审计可信
- Hash Chain：类似区块链，防篡改
- 因果链：通过 parent_id 追踪事件因果关系
- 状态外化：LLM 无状态，所有状态都在 EventLog 中

---

#### 3.2.3 IToolGateway（工具网关）

```python
"""
OS 对应：系统调用接口 (System Call Interface)
- Agent 与外部世界交互的唯一通道
- 所有工具调用必须经过这里
- 统一的验证、日志、监控入口
"""

@dataclass
class ToolCall:
    tool_id: str
    params: dict
    context: Optional[dict] = None

@dataclass
class ToolResult:
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)

class IToolGateway(Protocol):
    """工具执行网关 - 唯一的外部交互入口"""
    
    async def invoke(
        self,
        call: ToolCall,
        timeout: Optional[float] = None
    ) -> ToolResult:
        """
        执行工具调用
        内部流程:
        1. SecurityBoundary.verify() - 安全验证
        2. EventLog.append() - 记录调用
        3. 实际执行
        4. EventLog.append() - 记录结果
        """
        ...
    
    def register(self, tool: ITool) -> None:
        """注册工具"""
        ...
    
    def unregister(self, tool_id: str) -> None:
        """注销工具"""
        ...
    
    def list_tools(self) -> List[ToolDescriptor]:
        """列出所有可用工具"""
        ...
    
    def get_tool(self, tool_id: str) -> Optional[ITool]:
        """获取工具实例"""
        ...
```

**设计要点**：
- 单一入口：所有外部交互都经过 Gateway
- 职责分离：Gateway 只负责"调度"，安全检查委托给 SecurityBoundary
- 自动日志：每次调用自动记录到 EventLog

---

#### 3.2.4 ISecurityBoundary（安全边界）

```python
"""
OS 对应：MMU + 权限系统 + 沙箱
- 信任验证：LLM 输出是否可信？
- 权限检查：这个操作是否被允许？
- 沙箱执行：如何安全地执行？
"""

class RiskLevel(Enum):
    READ_ONLY = "read_only"           # 只读操作
    IDEMPOTENT_WRITE = "idempotent"   # 幂等写入
    NON_IDEMPOTENT = "non_idempotent" # 非幂等操作
    DESTRUCTIVE = "destructive"        # 破坏性操作

@dataclass
class VerifiedAction:
    """经过验证的动作"""
    original: ToolCall
    verified_tool_id: str       # 从 Registry 确认的 ID
    sanitized_params: dict      # 消毒后的参数
    risk_level: RiskLevel
    requires_approval: bool     # 是否需要人工批准
    sandbox_config: Optional[SandboxConfig] = None

class ISecurityBoundary(Protocol):
    """安全边界 - 信任验证 + 沙箱隔离"""
    
    # === 信任验证（执行前）===
    def verify(self, untrusted_call: ToolCall) -> VerifiedAction:
        """
        验证不可信的工具调用
        - 检查工具是否存在于 Registry
        - 参数消毒
        - 确定风险等级
        - 决定是否需要人工批准
        """
        ...
    
    def is_allowed(
        self,
        action: VerifiedAction,
        policy: Optional[Policy] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        检查动作是否被允许
        返回: (是否允许, 拒绝原因)
        """
        ...
    
    # === 沙箱执行（执行时）===
    def create_sandbox(self, config: SandboxConfig) -> ISandbox:
        """创建沙箱环境"""
        ...
    
    async def execute_sandboxed(
        self,
        action: VerifiedAction,
        executor: Callable
    ) -> ToolResult:
        """在沙箱中执行动作"""
        ...
```

**设计要点**：
- 合并 TrustBoundary + Sandbox：概念统一为"安全边界"
- 两阶段：验证（执行前）+ 隔离执行（执行时）
- 风险分级：不同风险级别触发不同策略

---

#### 3.2.5 IResourceManager（资源管理器）

```python
"""
OS 对应：内存管理器 (Memory Manager)
- Token 预算管理
- 成本控制
- Context Window 管理
- 执行时间限制
"""

class ResourceType(Enum):
    INPUT_TOKENS = "input_tokens"
    OUTPUT_TOKENS = "output_tokens"
    TOTAL_TOKENS = "total_tokens"
    API_COST = "api_cost"           # 美元
    EXECUTION_TIME = "execution_time"  # 秒
    TOOL_CALLS = "tool_calls"       # 调用次数
    CONTEXT_WINDOW = "context_window"  # Context 占用

@dataclass
class ResourceBudget:
    resource_type: ResourceType
    limit: float
    current: float = 0.0
    
    @property
    def remaining(self) -> float:
        return self.limit - self.current
    
    @property
    def exhausted(self) -> bool:
        return self.current >= self.limit

class IResourceManager(Protocol):
    """资源管理器 - 预算和限制"""
    
    def set_budget(self, resource_type: ResourceType, limit: float) -> None:
        """设置资源预算"""
        ...
    
    def consume(self, resource_type: ResourceType, amount: float) -> bool:
        """
        消耗资源
        返回: 是否成功（False 表示预算不足）
        """
        ...
    
    def get_remaining(self, resource_type: ResourceType) -> float:
        """获取剩余预算"""
        ...
    
    def get_usage(self) -> Dict[ResourceType, ResourceBudget]:
        """获取所有资源使用情况"""
        ...
    
    def estimate(self, action: ToolCall) -> Dict[ResourceType, float]:
        """预估动作的资源消耗"""
        ...
    
    def on_budget_exceeded(
        self,
        resource_type: ResourceType,
        handler: Callable[[ResourceType, float], None]
    ) -> None:
        """注册预算超限处理器"""
        ...
```

**设计要点**：
- 多维度预算：Token、成本、时间都是"资源"
- 预估能力：执行前可以预估消耗
- 软/硬限制：可配置超限时的行为（警告/停止）

---

#### 3.2.6 IExecutionControl（执行控制）

```python
"""
OS 对应：中断处理器 (Interrupt Handler) + 进程状态管理
- 暂停/恢复执行
- Checkpoint/Restore
- 信号处理
"""

class Signal(Enum):
    PAUSE = "pause"           # 暂停
    RESUME = "resume"         # 恢复
    CANCEL = "cancel"         # 取消
    TIMEOUT = "timeout"       # 超时
    BUDGET_EXCEEDED = "budget_exceeded"  # 预算超限
    HUMAN_INTERVENTION = "human_intervention"  # HITL

@dataclass
class Checkpoint:
    id: str
    created_at: datetime
    state: AgentState
    event_log_position: str   # EventLog 中的位置
    context: dict             # 上下文快照
    metadata: dict

class IExecutionControl(Protocol):
    """执行控制 - 中断 + 状态管理"""
    
    # === 执行控制 ===
    async def pause(self) -> Checkpoint:
        """暂停执行，自动创建 checkpoint"""
        ...
    
    async def resume(self, checkpoint_id: Optional[str] = None) -> None:
        """恢复执行，可选从指定 checkpoint 恢复"""
        ...
    
    async def cancel(self, reason: str, save_checkpoint: bool = True) -> Optional[Checkpoint]:
        """取消执行"""
        ...
    
    # === 信号处理 ===
    def send_signal(self, signal: Signal, payload: Optional[dict] = None) -> None:
        """发送信号"""
        ...
    
    def on_signal(self, signal: Signal, handler: Callable[[Signal, dict], None]) -> None:
        """注册信号处理器"""
        ...
    
    # === Checkpoint 管理 ===
    def create_checkpoint(self, metadata: Optional[dict] = None) -> Checkpoint:
        """手动创建 checkpoint"""
        ...
    
    def restore_checkpoint(self, checkpoint_id: str) -> None:
        """恢复到指定 checkpoint"""
        ...
    
    def list_checkpoints(self) -> List[Checkpoint]:
        """列出所有 checkpoints"""
        ...
    
    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """删除 checkpoint"""
        ...
```

**设计要点**：
- 合并中断和状态：Checkpoint 是中断处理的内在需求
- 信号机制：类似 Unix 信号，支持自定义处理
- 自动化：暂停时自动创建 checkpoint

---

#### 3.2.7 IExtensionPoint（扩展点）

```python
"""
OS 对应：内核模块接口 (Kernel Module Interface)
- 生命周期钩子
- 允许在不修改核心代码的情况下扩展行为
"""

class HookPhase(Enum):
    # Agent 生命周期
    BEFORE_RUN = "before_run"
    AFTER_RUN = "after_run"
    
    # 循环阶段
    BEFORE_PLAN = "before_plan"
    AFTER_PLAN = "after_plan"
    BEFORE_EXECUTE = "before_execute"
    AFTER_EXECUTE = "after_execute"
    BEFORE_VALIDATE = "before_validate"
    AFTER_VALIDATE = "after_validate"
    
    # 工具调用
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    
    # 状态变化
    ON_STATE_CHANGE = "on_state_change"
    ON_ERROR = "on_error"
    ON_CHECKPOINT = "on_checkpoint"

class IHook(Protocol):
    """钩子接口"""
    
    @property
    def phase(self) -> HookPhase:
        """触发阶段"""
        ...
    
    @property
    def priority(self) -> int:
        """优先级（数字越小越先执行）"""
        ...
    
    async def execute(self, context: HookContext) -> HookResult:
        """执行钩子"""
        ...

class IExtensionPoint(Protocol):
    """扩展点管理器"""
    
    def register_hook(self, hook: IHook) -> None:
        """注册钩子"""
        ...
    
    def unregister_hook(self, hook_id: str) -> None:
        """注销钩子"""
        ...
    
    async def trigger(self, phase: HookPhase, context: HookContext) -> List[HookResult]:
        """触发某阶段的所有钩子"""
        ...
    
    def list_hooks(self, phase: Optional[HookPhase] = None) -> List[IHook]:
        """列出钩子"""
        ...
```

**设计要点**：
- 非侵入式扩展：不修改核心代码即可添加功能
- 优先级控制：多个钩子时按优先级执行
- 典型用途：日志、监控、调试、自定义策略

---

### 3.3 Kernel 层接口依赖关系

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Kernel 内部依赖关系                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                          ┌──────────────┐                               │
│                          │  IRunLoop    │ ◄─────────────────────┐       │
│                          │  (调度核心)  │                       │       │
│                          └──────┬───────┘                       │       │
│                                 │                               │       │
│            ┌────────────────────┼────────────────────┐          │       │
│            │                    │                    │          │       │
│            ▼                    ▼                    ▼          │       │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │       │
│   │ IToolGateway │    │ IEventLog    │    │IExtensionPt  │     │       │
│   │ (工具执行)   │    │ (事件记录)   │    │ (扩展钩子)   │     │       │
│   └──────┬───────┘    └──────────────┘    └──────────────┘     │       │
│          │                    ▲                                 │       │
│          │                    │ (所有操作都记录)                │       │
│          ▼                    │                                 │       │
│   ┌──────────────┐           │                                 │       │
│   │ISecurity     │───────────┘                                 │       │
│   │Boundary      │                                             │       │
│   │(安全验证)    │                                             │       │
│   └──────────────┘                                             │       │
│                                                                │       │
│   ┌──────────────┐    ┌──────────────┐                        │       │
│   │IResource     │    │IExecution    │────────────────────────┘       │
│   │Manager       │    │Control       │                                │
│   │(资源预算)    │    │(中断/状态)   │                                │
│   └──────────────┘    └──────────────┘                                │
│          │                    │                                        │
│          └────────────────────┘                                        │
│                    │                                                   │
│                    ▼                                                   │
│           (预算超限触发中断)                                           │
│                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 四、Layer 1.5: Protocol Adapters（协议适配层）

### 4.1 设计理念

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            协议 vs 实现                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   协议定义：如何通信？消息格式是什么？                                   │
│   实现提供：具体的工具/Agent/UI 组件                                     │
│                                                                         │
│   ┌─────────────┐                                                       │
│   │   MCP       │ ──► 工具接入协议（定义如何发现和调用工具）             │
│   └─────────────┘                                                       │
│         │                                                               │
│         ├──► Stdio Transport                                            │
│         ├──► SSE Transport                                              │
│         └──► HTTP Transport                                             │
│                                                                         │
│   ┌─────────────┐                                                       │
│   │   A2A       │ ──► Agent 间通信协议（定义 Agent 如何协作）            │
│   └─────────────┘                                                       │
│         │                                                               │
│         ├──► HTTP Transport                                             │
│         └──► gRPC Transport                                             │
│                                                                         │
│   ┌─────────────┐                                                       │
│   │   A2UI      │ ──► Agent-UI 通信协议（定义如何与用户界面交互）        │
│   └─────────────┘                                                       │
│         │                                                               │
│         ├──► WebSocket Transport                                        │
│         └──► SSE Transport                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 统一协议接口

```python
"""
所有协议适配器实现同一个接口
框架只关心这个接口，不关心具体协议
"""

class CapabilityType(Enum):
    TOOL = "tool"           # MCP: 工具
    AGENT = "agent"         # A2A: 其他 Agent
    UI_COMPONENT = "ui"     # A2UI: UI 组件

@dataclass
class Capability:
    id: str
    type: CapabilityType
    name: str
    description: str
    schema: dict            # 输入输出 schema
    metadata: dict

class IProtocolAdapter(Protocol):
    """协议适配器统一接口"""
    
    @property
    def protocol_name(self) -> str:
        """协议名称: 'mcp', 'a2a', 'a2ui'"""
        ...
    
    async def connect(self, endpoint: str, config: dict) -> None:
        """建立连接"""
        ...
    
    async def disconnect(self) -> None:
        """断开连接"""
        ...
    
    async def discover(self) -> List[Capability]:
        """发现对端提供的能力"""
        ...
    
    async def invoke(
        self,
        capability_id: str,
        params: dict,
        timeout: Optional[float] = None
    ) -> Any:
        """调用能力"""
        ...
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable[[dict], None]
    ) -> Callable[[], None]:
        """订阅事件，返回取消订阅函数"""
        ...
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        ...
```

### 4.3 具体协议实现

```python
# MCP 协议适配器
class MCPAdapter(IProtocolAdapter):
    """MCP 协议 - 工具接入"""
    
    protocol_name = "mcp"
    
    def __init__(self, transport: MCPTransport):
        self.transport = transport  # Stdio / SSE / HTTP
    
    async def discover(self) -> List[Capability]:
        # 调用 MCP 的 tools/list
        tools = await self.transport.call("tools/list")
        return [
            Capability(
                id=t["name"],
                type=CapabilityType.TOOL,
                name=t["name"],
                description=t.get("description", ""),
                schema=t.get("inputSchema", {}),
                metadata={}
            )
            for t in tools
        ]

# A2A 协议适配器
class A2AAdapter(IProtocolAdapter):
    """A2A 协议 - Agent 间通信"""
    
    protocol_name = "a2a"
    
    async def discover(self) -> List[Capability]:
        # 获取其他 Agent 的 Agent Card
        agent_cards = await self._fetch_agent_cards()
        return [
            Capability(
                id=card["id"],
                type=CapabilityType.AGENT,
                name=card["name"],
                description=card["description"],
                schema=card.get("skills", {}),
                metadata=card
            )
            for card in agent_cards
        ]

# A2UI 协议适配器  
class A2UIAdapter(IProtocolAdapter):
    """A2UI 协议 - Agent-UI 通信"""
    
    protocol_name = "a2ui"
    
    async def invoke(self, capability_id: str, params: dict, timeout: Optional[float] = None) -> Any:
        # 向 UI 发送渲染指令
        if capability_id == "render":
            await self._send_to_ui("render", params)
        elif capability_id == "request_input":
            return await self._request_user_input(params, timeout)
```

### 4.4 协议层与 Kernel 的关系

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     协议层如何接入 Kernel                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   IToolGateway                                                          │
│       │                                                                 │
│       ├── Native Tools (直接注册的工具)                                 │
│       │       └── ReadFileTool, WriteFileTool, ...                     │
│       │                                                                 │
│       └── Protocol Adapters (协议接入的工具)                            │
│               │                                                         │
│               ├── MCPAdapter                                            │
│               │       └── FS Server (read, write, list)                │
│               │       └── Git Server (commit, push, pull)              │
│               │                                                         │
│               ├── A2AAdapter                                            │
│               │       └── SubAgent (delegate tasks)                    │
│               │       └── ReviewerAgent (code review)                  │
│               │                                                         │
│               └── A2UIAdapter                                           │
│                       └── render, request_input, show_progress         │
│                                                                         │
│   对 IToolGateway 来说，所有能力都是"工具"                              │
│   协议层只是工具的一种来源                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 五、Layer 2: Pluggable Components（可插拔组件层）

### 5.1 组件分类

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Layer 2 组件分类                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 模型适配 (Model Adapters)                                        │   │
│  │                                                                   │   │
│  │   IModelAdapter                                                   │   │
│  │   ├── ClaudeAdapter       (Anthropic API)                        │   │
│  │   ├── OpenAIAdapter       (OpenAI API)                           │   │
│  │   ├── OllamaAdapter       (本地模型)                             │   │
│  │   └── AzureOpenAIAdapter  (Azure 托管)                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 记忆系统 (Memory)                                                │   │
│  │                                                                   │   │
│  │   IMemory                                                         │   │
│  │   ├── InMemoryMemory      (开发测试)                             │   │
│  │   ├── VectorMemory        (语义检索)                             │   │
│  │   ├── FileMemory          (文件持久化)                           │   │
│  │   └── PostgresMemory      (生产环境)                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 执行工具 (Execute Tools)                                         │   │
│  │                                                                   │   │
│  │   ITool                                                           │   │
│  │   ├── ReadFileTool        (READ_ONLY)                            │   │
│  │   ├── WriteFileTool       (IDEMPOTENT_WRITE)                     │   │
│  │   ├── RunCommandTool      (NON_IDEMPOTENT)                       │   │
│  │   ├── GitPushTool         (DESTRUCTIVE)                          │   │
│  │   └── ...                                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 规划工具 / 技能 (Plan Tools / Skills)                            │   │
│  │                                                                   │   │
│  │   ISkill                                                          │   │
│  │   ├── FixFailingTestSkill                                        │   │
│  │   ├── ImplementFeatureSkill                                      │   │
│  │   ├── RefactorModuleSkill                                        │   │
│  │   └── ...                                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 策略组件 (Strategy Components) - 可替换的算法                    │   │
│  │                                                                   │   │
│  │   IPlanner          (规划策略)                                    │   │
│  │   ├── LLMPlanner           (基于 LLM 生成计划)                   │   │
│  │   ├── SearchPlanner        (基于搜索的规划)                      │   │
│  │   └── HybridPlanner        (混合策略)                            │   │
│  │                                                                   │   │
│  │   IValidator        (验证策略)                                    │   │
│  │   ├── LLMValidator         (LLM 判断)                            │   │
│  │   ├── RuleValidator        (规则验证)                            │   │
│  │   └── CompositeValidator   (组合验证)                            │   │
│  │                                                                   │   │
│  │   IRemediator       (修复策略)                                    │   │
│  │   ├── LLMRemediator        (LLM 反思)                            │   │
│  │   └── RuleRemediator       (规则修复)                            │   │
│  │                                                                   │   │
│  │   IContextBuilder   (上下文构建策略)                              │   │
│  │   ├── SlidingWindowContext (滑动窗口)                            │   │
│  │   ├── RAGContext           (检索增强)                            │   │
│  │   └── SummarizingContext   (摘要压缩)                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 钩子 (Hooks) - 扩展点的实现                                      │   │
│  │                                                                   │   │
│  │   IHook                                                           │   │
│  │   ├── LoggingHook          (日志记录)                            │   │
│  │   ├── MetricsHook          (指标收集)                            │   │
│  │   ├── TracingHook          (分布式追踪)                          │   │
│  │   └── CostTrackingHook     (成本追踪)                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 组件接口定义

```python
# === 模型适配器 ===
class IModelAdapter(Protocol):
    """模型适配器接口"""
    
    @property
    def model_id(self) -> str: ...
    
    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDescriptor]] = None,
        **kwargs
    ) -> ModelResponse: ...
    
    async def stream(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDescriptor]] = None,
        **kwargs
    ) -> AsyncIterator[ModelChunk]: ...

# === 记忆系统 ===
class IMemory(Protocol):
    """记忆系统接口"""
    
    async def store(self, key: str, value: Any, metadata: Optional[dict] = None) -> None: ...
    async def retrieve(self, key: str) -> Optional[Any]: ...
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]: ...
    async def delete(self, key: str) -> None: ...

# === 工具 ===
class ITool(Protocol):
    """工具接口"""
    
    @property
    def id(self) -> str: ...
    
    @property
    def description(self) -> str: ...
    
    @property
    def parameters_schema(self) -> dict: ...
    
    @property
    def risk_level(self) -> RiskLevel: ...
    
    async def execute(self, params: dict) -> ToolResult: ...

# === 技能 ===
class ISkill(Protocol):
    """技能接口（Plan Tool）"""
    
    @property
    def id(self) -> str: ...
    
    @property
    def description(self) -> str: ...
    
    @property
    def allowed_tools(self) -> List[str]: ...
    
    def generate_prompt(self, context: SkillContext) -> str: ...
    
    def parse_result(self, llm_output: str) -> SkillResult: ...

# === 策略组件 ===
class IPlanner(Protocol):
    """规划器接口"""
    
    async def generate_plan(self, task: Task, context: PlanContext) -> Plan: ...

class IValidator(Protocol):
    """验证器接口"""
    
    async def validate(self, result: StepResult, context: ValidationContext) -> ValidationResult: ...

class IRemediator(Protocol):
    """修复器接口"""
    
    async def remediate(self, failure: ValidationFailure, context: RemediationContext) -> RemediationResult: ...

class IContextBuilder(Protocol):
    """上下文构建器接口"""
    
    async def build(self, task: Task, history: List[Event]) -> Context: ...
```

---

## 六、Layer 3: Developer API（开发者接口层）

### 6.1 Fluent Builder API

```python
"""
开发者使用的高层 API
目标：简单场景简单用，复杂场景有能力定制
"""

class AgentBuilder(Generic[DepsT, OutputT]):
    """Agent 构建器 - Fluent API"""
    
    def __init__(self):
        self._model: Optional[IModelAdapter] = None
        self._tools: List[ITool] = []
        self._skills: List[ISkill] = []
        self._memory: Optional[IMemory] = None
        self._protocols: List[IProtocolAdapter] = []
        self._hooks: List[IHook] = []
        self._planner: Optional[IPlanner] = None
        self._validator: Optional[IValidator] = None
        self._config: AgentConfig = AgentConfig()
    
    def with_model(self, model: IModelAdapter) -> "AgentBuilder[DepsT, OutputT]":
        """设置模型"""
        self._model = model
        return self
    
    def with_tools(self, *tools: ITool) -> "AgentBuilder[DepsT, OutputT]":
        """添加工具"""
        self._tools.extend(tools)
        return self
    
    def with_skills(self, *skills: ISkill) -> "AgentBuilder[DepsT, OutputT]":
        """添加技能"""
        self._skills.extend(skills)
        return self
    
    def with_memory(self, memory: IMemory) -> "AgentBuilder[DepsT, OutputT]":
        """设置记忆系统"""
        self._memory = memory
        return self
    
    def with_mcp(self, endpoint: str, transport: str = "stdio") -> "AgentBuilder[DepsT, OutputT]":
        """添加 MCP 服务器"""
        adapter = MCPAdapter(endpoint, transport)
        self._protocols.append(adapter)
        return self
    
    def with_a2a(self, agent_url: str) -> "AgentBuilder[DepsT, OutputT]":
        """添加 A2A 连接"""
        adapter = A2AAdapter(agent_url)
        self._protocols.append(adapter)
        return self
    
    def with_hooks(self, *hooks: IHook) -> "AgentBuilder[DepsT, OutputT]":
        """添加钩子"""
        self._hooks.extend(hooks)
        return self
    
    def with_planner(self, planner: IPlanner) -> "AgentBuilder[DepsT, OutputT]":
        """设置自定义规划器"""
        self._planner = planner
        return self
    
    def with_budget(
        self,
        max_tokens: Optional[int] = None,
        max_cost: Optional[float] = None,
        max_time: Optional[float] = None
    ) -> "AgentBuilder[DepsT, OutputT]":
        """设置资源预算"""
        if max_tokens:
            self._config.budgets[ResourceType.TOTAL_TOKENS] = max_tokens
        if max_cost:
            self._config.budgets[ResourceType.API_COST] = max_cost
        if max_time:
            self._config.budgets[ResourceType.EXECUTION_TIME] = max_time
        return self
    
    def build(self) -> "Agent[DepsT, OutputT]":
        """构建 Agent"""
        return Agent(
            model=self._model,
            tools=self._tools,
            skills=self._skills,
            memory=self._memory,
            protocols=self._protocols,
            hooks=self._hooks,
            planner=self._planner or LLMPlanner(),
            validator=self._validator or CompositeValidator(),
            config=self._config
        )

# 使用示例
agent = (
    AgentBuilder()
    .with_model(ClaudeAdapter("claude-sonnet-4-20250514"))
    .with_tools(ReadFileTool(), WriteFileTool(), RunTestsTool())
    .with_skills(FixFailingTestSkill())
    .with_mcp("npx -y @anthropic/mcp-server-filesystem")
    .with_memory(VectorMemory())
    .with_hooks(LoggingHook(), MetricsHook())
    .with_budget(max_tokens=100000, max_cost=1.0)
    .build()
)

result = await agent.run("Fix the failing test in auth_test.py")
```

---

## 七、核心与锦上添花的划分

### 7.1 必须有的（跑起来的最小集）

| 组件 | 理由 |
|------|------|
| `IRunLoop` | 没有调度器，Agent 无法运行 |
| `IEventLog` | 没有日志，无法调试、审计、恢复 |
| `IToolGateway` | 没有工具调用，Agent 无法影响外部世界 |
| `ISecurityBoundary` | 没有安全边界，LLM 输出直接执行太危险 |

### 7.2 重要的（生产环境需要）

| 组件 | 理由 |
|------|------|
| `IResourceManager` | 没有预算控制，成本可能失控 |
| `IExecutionControl` | 没有中断/恢复，长任务难以管理 |
| `IExtensionPoint` | 没有扩展点，定制化困难 |

### 7.3 锦上添花的（Layer 2）

| 组件 | 理由 |
|------|------|
| 各种 `IModelAdapter` | 支持不同 LLM 是好事，但框架可以只支持一种 |
| 各种 `IMemory` | 不同持久化方案是便利，不是必须 |
| 各种 `IPlanner/IValidator` | 策略可替换是高级用法 |
| Protocol Adapters | MCP/A2A 是生态集成，不是核心运行依赖 |

### 7.4 对比 OS

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         OS vs Agent Framework                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   OS 必须有:                        Agent 必须有:                        │
│   ├── 进程调度器                    ├── IRunLoop                        │
│   ├── 系统调用接口                  ├── IToolGateway                    │
│   ├── 安全边界 (Ring 0/3)           ├── ISecurityBoundary               │
│   └── 基本日志/审计                 └── IEventLog                       │
│                                                                         │
│   OS 重要的:                        Agent 重要的:                        │
│   ├── 内存管理                      ├── IResourceManager                │
│   ├── 中断处理                      ├── IExecutionControl               │
│   └── 内核模块接口                  └── IExtensionPoint                 │
│                                                                         │
│   OS 锦上添花:                      Agent 锦上添花:                      │
│   ├── 各种文件系统                  ├── 各种 Memory 实现                │
│   ├── 各种网络协议                  ├── 各种 Protocol Adapters          │
│   ├── 各种设备驱动                  ├── 各种 Tools/Skills               │
│   └── 各种桌面环境                  └── 各种 Planners/Validators        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 八、总结

### 8.1 架构全景

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        DARE Framework 最终架构                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   Layer 3: Developer API                                                      ║
║   └── AgentBuilder / Fluent API / Configuration                              ║
║                                                                               ║
║   Layer 2: Pluggable Components                                               ║
║   ├── Model Adapters: Claude, OpenAI, Ollama, ...                            ║
║   ├── Memory: InMemory, Vector, File, Postgres, ...                          ║
║   ├── Tools: ReadFile, WriteFile, RunCommand, ...                            ║
║   ├── Skills: FixTest, ImplementFeature, Refactor, ...                       ║
║   ├── Strategies: Planners, Validators, Remediators, ContextBuilders         ║
║   └── Hooks: Logging, Metrics, Tracing, ...                                  ║
║                                                                               ║
║   Layer 1.5: Protocol Adapters                                                ║
║   ├── MCP Adapter (Tool Protocol)                                            ║
║   ├── A2A Adapter (Agent Protocol)                                           ║
║   └── A2UI Adapter (UI Protocol)                                             ║
║                                                                               ║
║   Layer 1: Kernel (7 Core Interfaces)                                         ║
║   ├── IRunLoop           (进程调度)         🔴 必须                           ║
║   ├── IEventLog          (审计日志)         🔴 必须                           ║
║   ├── IToolGateway       (系统调用)         🔴 必须                           ║
║   ├── ISecurityBoundary  (安全边界)         🔴 必须                           ║
║   ├── IResourceManager   (资源管理)         🟡 重要                           ║
║   ├── IExecutionControl  (中断处理)         🟡 重要                           ║
║   └── IExtensionPoint    (扩展接口)         🟡 重要                           ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 8.2 我的核心观点

1. **Kernel 应该尽可能小**：只放"没有就跑不起来"的东西
2. **IEventLog 是核心**：LLM 无状态，所有状态都在日志中
3. **安全边界是核心**：LLM 输出不可信，必须有验证
4. **策略是插件**：Planner/Validator/Remediator 都应该可替换
5. **协议是桥梁**：MCP/A2A 是接入方式，不是工具本身
6. **面向未来设计**：AI 技术剧变时，Kernel 接口应该稳定

---

*本文档是 Claude 基于与用户讨论后的架构设计观点，供 Claude Code 参考和合并。*