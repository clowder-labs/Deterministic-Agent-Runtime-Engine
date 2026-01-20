# DARE Framework 架构对比分析：v1 vs v2 与 v3 愿景

> **分析日期**: 2026-01-19
> **对比范围**: dare_framework (master) vs dare_framework2 (framework2)
> **参考文档**: doc/design/Architecture_Final_Review_v2.1.md

---

## 🆕 v3.1 架构设计

> **设计日期**: 2026-01-19
> **基于**: v3 架构 + 用户 API 讨论 + 模块职责分析

---

### 一、设计目标

| 目标 | 说明 |
|------|------|
| 简化用户 API | 用户只需了解 Agent 类，不需要同时理解 Builder 和 Preset |
| 执行策略可扩展 | 用户可通过继承 BaseAgent 实现任意执行模式 |
| Kernel 更纯粹 | 只保留真正的基础设施，移除策略性接口 |
| 依赖倒置 | 通过工厂函数隔离 impl 细节，高层不直接依赖低层实现 |
| 只重构不新增 | 保持与原代码对应，新功能仅放占位 |

---

### 二、用户 API

#### 2.1 使用方式

```python
from dare_framework2.agent import FiveLayerAgent, BaseAgent

# 方式 1：预定义 Agent + 默认配置
agent = FiveLayerAgent(name="my-agent", model=model, tools=[tool1, tool2])
result = await agent.run("完成这个任务")

# 方式 2：预定义 Agent + 定制组件
agent = FiveLayerAgent(
    name="my-agent",
    model=model,
    tools=[tool1, tool2],
    planner=MyPlanner(),
    validator=MyValidator(),
    budget=Budget(max_tool_calls=100),
    config=config,                    # 可选配置
    protocol_adapters=[mcp_adapter],  # 可选协议适配器
)

# 方式 3：继承 BaseAgent 完全自定义
class MyReActAgent(BaseAgent):
    async def _execute(self, task: Task) -> RunResult:
        # 自定义执行逻辑，可使用 self._model, self._tools 等组件
        ...
```

#### 2.2 类继承关系

```
BaseAgent (抽象基类)
    ├── FiveLayerAgent      # 五层循环（从 DefaultLoopOrchestrator 迁移）
    ├── SimpleChatAgent     # 简单对话 [占位]
    └── [用户自定义]         # 继承 BaseAgent，实现 _execute()
```

---

### 三、目录结构

```
dare_framework2/
├── __init__.py                     # 导出 Agent 类
│
├── agent/                          # 【新增】用户 API 层
│   ├── __init__.py
│   ├── base.py                     # BaseAgent 抽象基类
│   ├── five_layer.py               # FiveLayerAgent
│   └── simple_chat.py              # SimpleChatAgent [占位]
│
├── runtime/                        # 运行时基础设施（原 execution/，重命名）
│   ├── __init__.py                 # 接口 + 工厂函数
│   ├── interfaces.py               # IExecutionControl, IResourceManager,
│   │                               # IEventLog, IExtensionPoint, IHook
│   ├── types.py
│   └── impl/
│
├── security/                       # 【新增】从 tool/ 独立
│   ├── __init__.py                 # 接口 + 工厂函数
│   ├── interfaces.py               # ISecurityBoundary
│   └── impl/
│
├── context/                        # 上下文管理
│   ├── __init__.py                 # 接口 + 工厂函数
│   ├── interfaces.py               # IContextManager
│   └── impl/
│
├── memory/                         # 记忆存储（保持独立）
│   ├── __init__.py
│   ├── interfaces.py               # IMemory, IPromptStore
│   └── impl/
│
├── tool/                           # 工具系统
│   ├── __init__.py                 # 接口 + 工厂函数
│   ├── interfaces.py               # IToolGateway (Layer 0)
│   │                               # IProtocolAdapter (Layer 1)
│   │                               # ITool, ICapabilityProvider (Layer 2)
│   └── impl/
│
├── plan/                           # 计划系统
│   ├── __init__.py                 # 接口 + 工厂函数
│   ├── interfaces.py               # IPlanner, IValidator, IRemediator
│   └── impl/
│
├── model/                          # 模型适配
│   ├── __init__.py
│   ├── interfaces.py               # IModelAdapter
│   └── impl/
│
├── config/                         # 配置管理
│   ├── __init__.py                 # 接口 + 工厂函数
│   ├── interfaces.py               # IConfigProvider
│   ├── types.py                    # Config, LLMConfig, ComponentConfig
│   └── impl/
│
└── utils/                          # 通用工具
    ├── __init__.py
    ├── errors.py                   # 异常类型
    ├── ids.py                      # ID 生成
    └── types.py                    # 从 builder/types.py 迁移的有用类型
```

---

### 四、Kernel 接口（7 个）

| 接口 | 域 | 职责 |
|------|-----|------|
| IExecutionControl | runtime | 暂停/恢复/检查点 |
| IResourceManager | runtime | 预算控制 |
| IEventLog | runtime | 审计日志 |
| IExtensionPoint | runtime | Hook 扩展 |
| IToolGateway | tool | 工具调用入口 |
| ISecurityBoundary | security | 安全边界 |
| IContextManager | context | 上下文组装 |

**移除的接口**：
- `IRunLoop` → `Agent.run()` 替代
- `ILoopOrchestrator` → `FiveLayerAgent._execute()` 替代

---

### 五、模块职责

| 模块 | 层级 | 职责 | v3.1 变化 |
|------|------|------|----------|
| agent/ | Layer 3 | 用户 API + 执行策略 | **新增** |
| runtime/ | Layer 0 | 运行时基础设施 | 原 execution/，移除 IRunLoop, ILoopOrchestrator |
| security/ | Layer 0 | 安全边界 | **新增**（从 tool/ 独立） |
| context/ | Layer 0 | 上下文组装 | 不变 |
| memory/ | Layer 2 | 记忆存储 | 保持独立 |
| tool/ | Layer 0/1/2 | 工具调用 + 协议适配 | 移除 ISecurityBoundary |
| plan/ | Layer 2 | 计划/验证/修复 | 不变 |
| model/ | Layer 1 | 模型适配 | 不变 |
| config/ | Layer 3 | 配置管理 | 不变，添加工厂函数 |
| utils/ | - | 通用工具 | 接收 builder/ 迁移的类型 |
| execution/ | - | - | **重命名为 runtime/** |
| builder/ | - | - | **删除** |

---

### 六、工厂函数模式

解决 builder.py 直接 import impl 的 DIP 违规问题：

```python
# runtime/__init__.py
from .interfaces import IResourceManager, IEventLog

def create_default_resource_manager(budget=None) -> IResourceManager:
    from .impl.in_memory_resource_manager import InMemoryResourceManager
    return InMemoryResourceManager(default_budget=budget)

def create_default_event_log(path: str) -> IEventLog:
    from .impl.local_event_log import LocalEventLog
    return LocalEventLog(path=path)
```

```python
# agent/base.py
class BaseAgent:
    def _build_resource_manager(self, budget):
        from dare_framework2.runtime import create_default_resource_manager
        return create_default_resource_manager(budget)
```

**好处**：BaseAgent 只依赖工厂函数，不知道具体实现类。

---

### 七、关键设计决策

| 决策 | 内容 | 理由 |
|------|------|------|
| Agent 类替代 Builder + Preset | 用户只需知道 Agent 类 | 降低学习成本，API 更直观 |
| ILoopOrchestrator 移到 Agent | 五层循环是执行策略 | Kernel 只放基础设施，不放策略 |
| IRunLoop 移除 | Agent.run() 直接驱动 | 减少不必要的抽象层 |
| Security 独立成域 | ISecurityBoundary 被多域使用 | 不应依附于 tool/ |
| Memory 保持独立 | Context 依赖 IMemory 接口即可 | 符合依赖倒置，不需要物理合并 |
| IProtocolAdapter 保留在 tool/ | 与 IToolGateway 关系紧密 | 用注释标注 Layer 1，不单独建目录 |
| config/ 保持独立 | 配置管理是独立功能 | Agent 可选择性使用 config 参数 |
| 删除 builder/ | 职责被 BaseAgent 吸收 | 避免职责重叠 |

---

### 八、实施任务

#### ✅ 需要做的

| 任务 | 说明 |
|------|------|
| 创建 agent/ | base.py, five_layer.py, simple_chat.py |
| 实现 BaseAgent | 组件组装 + run() |
| 实现 FiveLayerAgent | 从 DefaultLoopOrchestrator 迁移 |
| 重命名 execution/ → runtime/ | 更准确的模块命名 |
| 独立 security/ | 从 tool/ 提取 ISecurityBoundary |
| 添加工厂函数 | 各域 __init__.py |
| 移除 IRunLoop, ILoopOrchestrator | 从 runtime/interfaces.py |
| 删除相关 impl | default_run_loop.py, default_orchestrator.py |
| 删除 builder/ | 有用类型移到 utils/types.py |

#### ❌ 不需要做的

| 任务 | 原因 |
|------|------|
| 实现 SimpleChatAgent | 新功能，只放占位 |
| 合并 memory 到 context | 保持独立更合理 |
| 独立 protocols/ | IProtocolAdapter 保留在 tool/，注释标注层级 |

---

### 九、设计权衡

#### 优点

| 优点 | 说明 |
|------|------|
| 概念简化 | 用户只需理解 Agent 类，不需要 Builder + Preset |
| 扩展性强 | 继承 BaseAgent 可实现任意执行模式（ReAct、工作流等） |
| Kernel 更纯粹 | 只剩 7 个基础设施接口，无策略性代码 |
| 依赖正确 | 工厂函数解决了 DIP 违规 |
| API 直观 | 构造函数参数比链式调用更清晰 |

#### 潜在问题

| 问题 | 应对 |
|------|------|
| FiveLayerAgent 代码量大（~700 行） | 拆分为 5 个私有方法（_run_xxx_loop），每个 ~100-150 行 |
| 失去 tick-by-tick 调试 | 可在 Agent 内部实现调试模式，或通过 Hook 机制 |
| 链式调用的动态组合能力丢失 | 影响小，复杂场景可继承 BaseAgent |

---

## 前言：理解 DARE 的四层架构

根据 Architecture_Final_Review_v2.1.md，DARE Framework 采用严格的四层架构：

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Developer API                                      │
│  - AgentBuilder / Fluent API / sensible defaults            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Pluggable Components                               │
│  - Strategies: IPlanner / IValidator / IRemediator          │
│  - Capabilities: IModelAdapter / IMemory / ICapabilityProvider│
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Protocol Adapters                                  │
│  - IProtocolAdapter (MCP / A2A / A2UI)                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 0: Kernel (9 个不可变核心接口)                         │
│  1. IRunLoop           - 状态机心跳                          │
│  2. ILoopOrchestrator  - 五层循环骨架                        │
│  3. IExecutionControl  - 暂停/恢复/checkpoint                │
│  4. IContextManager    - 上下文工程总负责人                   │
│  5. IResourceManager   - 统一预算模型                        │
│  6. IEventLog          - WORM 真理来源                       │
│  7. IToolGateway       - 系统调用接口                        │
│  8. ISecurityBoundary  - Trust+Policy+Sandbox                │
│  9. IExtensionPoint    - 系统级扩展点                        │
└─────────────────────────────────────────────────────────────┘
```

**关键原则**：
- **Kernel 只放不变的东西**：调度、资源、IO、安全、审计的基础设施
- **策略算法下放为组件**：Planner、Validator、Remediator 都是可插拔的
- **协议与实现分离**：MCP/A2A/A2UI 通过 Protocol Adapter 接入

---

## 一、dare_framework (v1) 架构分析

### 1.1 目录结构

```
dare_framework/
├── core/                    # Layer 0: Kernel（按 Kernel 接口划分）
│   ├── run_loop/           # IRunLoop
│   ├── orchestrator/       # ILoopOrchestrator
│   ├── execution_control/  # IExecutionControl
│   ├── context/            # IContextManager
│   ├── budget/             # IResourceManager
│   ├── event/              # IEventLog
│   ├── tool/               # IToolGateway
│   ├── security/           # ISecurityBoundary
│   ├── hook/               # IExtensionPoint
│   └── plan/               # Types only (not Kernel)
├── protocols/              # Layer 1
├── components/             # Layer 2
├── contracts/              # 跨层共享类型
└── builder.py              # Layer 3
```

**特点**：按 Kernel 接口划分，9 个域清晰对应 9 个 Kernel 接口

### 1.2 v1 的问题

❌ **过于碎片化**
- 9 个小目录，认知负担重
- 相关功能分散（如 Memory 在 components/ 而不是 context/）
- 难以看出功能域的整体关系

❌ **组织不够内聚**
- Kernel 和它的协作组件分离
- 例如：IContextManager 在 core/context/，但 IMemory 在 components/memory/

---

## 二、dare_framework2 (v2) 架构分析

### 2.1 目录结构

```
dare_framework2/
├── execution/              # 调度相关
│   ├── interfaces.py      # IRunLoop, ILoopOrchestrator, IExecutionControl,
│   │                      # IResourceManager, IEventLog, IExtensionPoint
│   ├── types.py
│   └── impl/
├── context/                # 上下文工程
│   ├── interfaces.py      # IContextManager, IContextStrategy
│   └── impl/
├── memory/                 # ⚠️ 独立成域
│   ├── interfaces.py      # IMemory, IPromptStore
│   └── impl/
├── tool/                   # 工具 + 安全（⚠️ 混在一起）
│   ├── interfaces.py      # IToolGateway, ITool + ISecurityBoundary 相关
│   └── impl/
├── plan/                   # 规划策略
│   ├── interfaces.py      # IPlanner, IValidator, IRemediator
│   └── impl/
├── model/                  # 模型适配器
│   ├── interfaces.py      # IModelAdapter
│   └── impl/
├── protocols/              # 协议适配层
└── builder/                # 开发者 API
```

### 2.2 v2 的优点

✅ **按功能域垂直切分** - 这是 v2 的核心价值
- 相关的东西放在一起
- 每个域内聚：interfaces.py + types.py + impl/
- 更符合直觉，易于理解

✅ **实用性强**
- 扁平化结构
- 代码量更少
- 快速上手

### 2.3 v2 的问题

❌ **memory/ 独立成域，但应该属于 Context Engineering**

根据 v2.1 规范，IContextManager 是上下文工程总负责人，协调四层：
```
L4 Orchestration → IContextManager 自己负责
L3 Assembly → IContextStrategy
L2 Retrieval → IMemory, IRetriever  ← Memory 在这里！
L1 Indexing → IIndexer
```

IMemory 是 IContextManager 的协作者，应该放在 context/ 域内。

❌ **ISecurityBoundary 依附于 tool/**

ISecurityBoundary 是 Kernel 的 9 个核心接口之一，负责系统级安全边界（Trust + Policy + Sandbox），不应该依附于 tool/ 模块。它需要被 context、execution、tool、model 等多个域使用。

❌ **Kernel 边界不清晰**

execution/interfaces.py 包含 6 个 Kernel 接口，但没有明确标识哪些是 Kernel、哪些是组件。

---

## 三、v3 混合式架构提案

### 3.1 核心设计思路

**结合两个版本的优点**：
- ✅ v2 的"功能域垂直切分"
- ✅ v1 的"Kernel 边界清晰"

**关键创新**：在每个域内用 `kernel.py` vs `components.py` 区分 Layer 0 和 Layer 2

### 3.2 完整 v3 架构

```
dare_framework_v3/
│
├── contracts/               # 跨域共享类型
│   ├── __init__.py
│   ├── types.py            # Task, Plan, Envelope, Budget, Event, etc.
│   ├── errors.py
│   └── ids.py
│
├── execution/               # 执行域（功能内聚）
│   ├── __init__.py
│   ├── kernel.py           # ┌─────────────────────────────────┐
│   │                       # │ Kernel 接口 (6 个)              │
│   │                       # │ - IRunLoop                      │
│   │                       # │ - ILoopOrchestrator             │
│   │                       # │ - IExecutionControl             │
│   │                       # │ - IResourceManager              │
│   │                       # │ - IEventLog                     │
│   │                       # │ - IExtensionPoint               │
│   │                       # └─────────────────────────────────┘
│   ├── types.py            # RunLoopState, TickResult, Budget, Event, etc.
│   └── impl/
│       ├── run_loop.py
│       ├── orchestrator.py
│       ├── execution_control.py
│       ├── resource_manager.py
│       ├── event_log.py
│       └── extension_point.py
│
├── context/                 # 上下文域（Context Engineering 体系）
│   ├── __init__.py
│   ├── kernel.py           # ┌─────────────────────────────────┐
│   │                       # │ Kernel 接口 (1 个)              │
│   │                       # │ - IContextManager               │
│   │                       # └─────────────────────────────────┘
│   ├── components.py       # ┌─────────────────────────────────┐
│   │                       # │ 组件接口（Context Engineering）  │
│   │                       # │ - IMemory        (L2 Retrieval) │ ← 从 memory/ 移入
│   │                       # │ - IRetriever     (L2 Retrieval) │
│   │                       # │ - IIndexer       (L1 Indexing)  │
│   │                       # │ - IContextStrategy (L3 Assembly)│
│   │                       # │ - IPromptStore   (L3 Assembly)  │ ← 从 memory/ 移入
│   │                       # └─────────────────────────────────┘
│   ├── types.py            # ContextStage, AssembledContext, etc.
│   └── impl/
│       ├── context_manager/
│       ├── memory/         # IMemory 实现（功能内聚！）
│       ├── retriever/      # IRetriever 实现
│       ├── indexer/        # IIndexer 实现
│       ├── strategies/     # IContextStrategy 实现
│       └── prompt_stores/  # IPromptStore 实现
│
├── security/                # 安全域（独立！）
│   ├── __init__.py
│   ├── kernel.py           # ┌─────────────────────────────────┐
│   │                       # │ Kernel 接口 (1 个)              │
│   │                       # │ - ISecurityBoundary             │ ← 从 tool/ 移出
│   │                       # └─────────────────────────────────┘
│   ├── components.py       # ┌─────────────────────────────────┐
│   │                       # │ 组件接口（可插拔子模块）         │
│   │                       # │ - ITrustVerifier                │
│   │                       # │ - IPolicyEngine                 │
│   │                       # │ - ISandbox                      │
│   │                       # └─────────────────────────────────┘
│   ├── types.py            # PolicyDecision, TrustedInput, SandboxSpec, etc.
│   └── impl/
│       ├── security_boundary.py
│       ├── trust/          # ITrustVerifier 实现
│       ├── policy/         # IPolicyEngine 实现
│       └── sandbox/        # ISandbox 实现
│
├── tool/                    # 工具域
│   ├── __init__.py
│   ├── kernel.py           # ┌─────────────────────────────────┐
│   │                       # │ Kernel 接口 (1 个)              │
│   │                       # │ - IToolGateway                  │
│   │                       # └─────────────────────────────────┘
│   ├── components.py       # ┌─────────────────────────────────┐
│   │                       # │ 组件接口                        │
│   │                       # │ - ICapabilityProvider           │
│   │                       # │ - ITool                         │
│   │                       # │ - ISkill                        │
│   │                       # └─────────────────────────────────┘
│   ├── types.py            # CapabilityDescriptor, ToolResult, etc.
│   └── impl/
│       ├── tool_gateway.py
│       ├── providers/      # Native, MCP, etc.
│       ├── tools/          # 具体工具
│       └── skills/         # 技能
│
├── plan/                    # 规划域（纯组件，无 Kernel）
│   ├── __init__.py
│   ├── components.py       # ┌─────────────────────────────────┐
│   │                       # │ 组件接口（Strategies）           │
│   │                       # │ - IPlanner                      │
│   │                       # │ - IValidator                    │
│   │                       # │ - IRemediator                   │
│   │                       # └─────────────────────────────────┘
│   ├── types.py            # ProposedPlan, ValidatedPlan, VerifyResult, etc.
│   └── impl/
│       ├── planners/
│       ├── validators/
│       └── remediators/
│
├── model/                   # 模型域（纯组件，无 Kernel）
│   ├── __init__.py
│   ├── components.py       # ┌─────────────────────────────────┐
│   │                       # │ 组件接口（Capabilities）         │
│   │                       # │ - IModelAdapter                 │
│   │                       # └─────────────────────────────────┘
│   ├── types.py            # ModelResponse, Message, etc.
│   └── impl/
│       ├── openai.py
│       ├── anthropic.py
│       └── mock.py
│
├── protocols/               # 协议适配层（Layer 1）
│   ├── __init__.py
│   ├── base.py             # IProtocolAdapter
│   ├── mcp/
│   ├── a2a/
│   └── a2ui/
│
├── presets/                 # 预设组合（乐高积木）
│   ├── __init__.py
│   ├── base.py             # Preset 基类
│   ├── minimal.py          # 最小 Agent
│   ├── autogpt.py          # AutoGPT 风格
│   └── reflexion.py        # Reflexion 风格
│
└── builder/                 # 开发者 API（Layer 3）
    ├── __init__.py
    ├── agent.py
    └── builder.py
```

### 3.3 Kernel 接口分布（共 9 个）

| 域 | Kernel 接口 | 数量 |
|---|---|---:|
| **execution/** | IRunLoop, ILoopOrchestrator, IExecutionControl, IResourceManager, IEventLog, IExtensionPoint | 6 |
| **context/** | IContextManager | 1 |
| **security/** | ISecurityBoundary | 1 |
| **tool/** | IToolGateway | 1 |
| **plan/** | (无 Kernel) | 0 |
| **model/** | (无 Kernel) | 0 |
| **总计** | | **9** |

### 3.4 关键设计决策

#### 决策 1：Memory 属于 Context Engineering

```python
# ❌ v2 设计：memory/ 独立成域
dare_framework2/
├── context/
│   └── interfaces.py   # IContextManager, IContextStrategy
├── memory/             # ← 独立
│   └── interfaces.py   # IMemory, IPromptStore

# ✅ v3 设计：Memory 放入 context/
dare_framework_v3/
├── context/
│   ├── kernel.py       # IContextManager
│   └── components.py   # IMemory, IRetriever, IIndexer, IContextStrategy, IPromptStore
```

**理由**：根据 v2.1 规范，上下文工程是一个完整体系：
```
IContextManager (Kernel) 协调：
├── L4 Orchestration → compress(), route()
├── L3 Assembly → IContextStrategy, IPromptStore
├── L2 Retrieval → IMemory, IRetriever  ← Memory 在这里！
└── L1 Indexing → IIndexer
```

#### 决策 2：Security 独立成域

```python
# ❌ v2 设计：Security 依附于 tool/
dare_framework2/
├── tool/
│   └── interfaces.py   # IToolGateway + ISecurityBoundary 相关类型

# ✅ v3 设计：Security 独立
dare_framework_v3/
├── security/
│   ├── kernel.py       # ISecurityBoundary (Kernel 接口)
│   └── components.py   # ITrustVerifier, IPolicyEngine, ISandbox
├── tool/
│   └── kernel.py       # IToolGateway (纯工具执行)
```

**理由**：
- ISecurityBoundary 是 Kernel 的 9 个核心接口之一
- 安全边界需要被多个域使用（context、execution、tool、model）
- 不应该依附于任何特定功能域

#### 决策 3：kernel.py vs components.py 区分

每个域内用文件名明确标识层级：
- `kernel.py` - Layer 0 Kernel 接口（不可变）
- `components.py` - Layer 2 组件接口（可插拔）

```python
# context/kernel.py
class IContextManager(Protocol):
    """Layer 0 Kernel: 上下文工程总负责人"""
    ...

# context/components.py
class IMemory(Protocol):
    """Layer 2 Component: 检索层实现"""
    ...

class IContextStrategy(Protocol):
    """Layer 2 Component: 组装层策略"""
    ...
```

#### 决策 4：Presets 系统

```python
# presets/autogpt.py
class AutoGPTPreset(Preset):
    """AutoGPT 风格：强规划 + 多工具 + 弱记忆"""

    @property
    def description(self) -> str:
        return "Goal-oriented autonomous agent with multi-step planning"

    def configure(self, builder: AgentBuilder) -> AgentBuilder:
        return (
            builder
            .with_planner(DeterministicPlanner(max_steps=10))
            .with_validator(StrictValidator())
            .with_remediator(ReflectiveRemediator())
            .with_memory(ShortTermMemory())
            .with_tools(
                FileSystemTools(),
                ShellTools(),
                BrowserTools(),
            )
        )

# 使用示例
agent = (
    AgentBuilder("my-agent")
    .with_preset(AutoGPTPreset())        # 快速上手
    .with_model(OpenAIAdapter("gpt-4"))  # 必须提供模型
    .build()
)
```

---

## 四、架构对比总结

| 维度 | v1 (dare_framework) | v2 (dare_framework2) | v3 (提案) |
|-----|-------------------|---------------------|----------|
| **组织方式** | 按 Kernel 接口划分 | 按功能域垂直切分 | 功能域 + kernel/components 区分 |
| **Kernel 边界** | ⭐⭐⭐⭐⭐ 清晰（9 个域） | ⭐⭐ 模糊 | ⭐⭐⭐⭐⭐ 清晰（kernel.py） |
| **功能内聚** | ⭐⭐ 分散 | ⭐⭐⭐⭐⭐ 内聚 | ⭐⭐⭐⭐⭐ 内聚 |
| **Memory 归属** | components/（错误） | memory/（错误） | context/（正确） |
| **Security 归属** | core/security/（正确） | tool/（错误） | security/（正确） |
| **学习曲线** | 陡峭 | 平缓 | 平缓 + Presets |
| **扩展性** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ Presets |

---

## 五、v3 vs v2 的关键改进

### 5.1 从 v2 迁移到 v3

| 变更 | v2 位置 | v3 位置 | 变更类型 |
|-----|--------|--------|---------|
| IMemory | memory/interfaces.py | context/components.py | 移动 |
| IPromptStore | memory/interfaces.py | context/components.py | 移动 |
| ISecurityBoundary | tool/interfaces.py | security/kernel.py | 移动 |
| ITrustVerifier | tool/types.py | security/components.py | 提升为接口 |
| IPolicyEngine | - | security/components.py | 新增 |
| ISandbox | - | security/components.py | 新增 |
| IRetriever | - | context/components.py | 新增 |
| IIndexer | - | context/components.py | 新增 |

### 5.2 保留 v2 的优点

✅ 功能域垂直切分（execution, context, tool, plan, model）
✅ 每个域内聚：interfaces + types + impl/
✅ 扁平化结构
✅ 快速上手的 API

### 5.3 修正 v2 的问题

✅ Memory 放入 Context Engineering 体系
✅ Security 独立成域
✅ kernel.py vs components.py 明确区分 Layer 0 和 Layer 2

### 5.4 新增能力

✅ Presets 系统（乐高式组合）
✅ 更完整的 Context Engineering 组件（IRetriever, IIndexer）
✅ Security 组件化（ITrustVerifier, IPolicyEngine, ISandbox）

---

## 六、实施建议

### Phase 1: 架构修正（基于 v2）

1. **将 memory/ 合并到 context/**
   ```bash
   # 移动文件
   mv dare_framework2/memory/interfaces.py dare_framework2/context/components.py
   mv dare_framework2/memory/impl/* dare_framework2/context/impl/memory/
   rm -r dare_framework2/memory/
   ```

2. **将 ISecurityBoundary 移到独立的 security/**
   ```bash
   mkdir dare_framework2/security
   # 从 tool/interfaces.py 提取 Security 相关内容到 security/kernel.py
   ```

3. **在每个域内添加 kernel.py vs components.py 区分**
   ```bash
   # execution/interfaces.py → execution/kernel.py
   # context/interfaces.py 拆分为 kernel.py + components.py
   ```

### Phase 2: 增强 Context Engineering

1. 添加 IRetriever 接口
2. 添加 IIndexer 接口
3. 完善 IContextManager 与这些组件的协作

### Phase 3: Security 组件化

1. 提取 ITrustVerifier 接口
2. 提取 IPolicyEngine 接口
3. 设计 ISandbox 接口（MVP 可以是 stub）

### Phase 4: Presets 系统

1. 设计 Preset 基类
2. 实现 MinimalPreset, AutoGPTPreset, ReflexionPreset
3. 完善 AgentBuilder 对 Preset 的支持

---

## 七、结论

### v3 的核心价值

1. **功能域垂直切分**（继承 v2）
   - execution, context, security, tool, plan, model
   - 每个域内聚，易于理解

2. **Kernel 边界清晰**（修正 v2）
   - kernel.py vs components.py 明确区分
   - 9 个 Kernel 接口归属正确

3. **Context Engineering 完整**（修正 v2）
   - Memory, Retriever, Indexer, ContextStrategy, PromptStore
   - 都属于 context/ 域

4. **Security 独立**（修正 v2）
   - 不依附于 tool/
   - 可被多个域使用

5. **乐高式组合**（新增）
   - Presets 系统
   - 快速上手 + 无限可能

### 最终建议

**立即行动**：
1. 合并 memory/ 到 context/
2. 独立 security/ 域
3. 添加 kernel.py vs components.py 区分

**持续演进**：
- 增强 Context Engineering 组件
- 组件化 Security
- 建立 Presets 生态

---

## 八、API 稳定性设计（用户无感升级）

### 8.1 问题分析：为什么其他框架经常破坏兼容性？

| 问题 | 典型场景 | 用户痛点 |
|-----|---------|---------|
| **直接导入内部模块** | `from langchain.llms.openai import OpenAI` | 内部重组后导入路径变化，代码崩溃 |
| **接口签名变化** | 方法参数、返回类型改变 | 升级后代码报错 |
| **无明确公开边界** | 用户不知道哪些 API 是稳定的 | 依赖了"私有" API |
| **无弃用过渡期** | 直接删除旧 API | 无时间迁移 |

### 8.2 v3 稳定性设计原则

#### 原则 1：Package Facade Pattern（包门面模式）

**核心思想**：用户只从顶级包导入，永远不直接导入内部模块

```python
# ✅ 正确用法（稳定）
from dare_framework import AgentBuilder, Agent
from dare_framework import IModelAdapter, IMemory, ITool
from dare_framework import Task, RunResult

# ❌ 错误用法（不稳定，可能在任何版本变化）
from dare_framework.context.impl.memory.vector import VectorMemory  # 内部路径
from dare_framework._internal.execution import DefaultRunLoop       # 私有模块
```

**实现**：

```python
# dare_framework/__init__.py - 🔒 稳定的公开 API

"""DARE Framework - Deterministic Agent Runtime Engine.

稳定 API 承诺：
- 从此文件导出的所有符号遵循 Semantic Versioning
- Minor 版本只添加功能，不删除/修改现有 API
- Major 版本变化会提前一个 Minor 版本标记弃用
"""

# === 核心 API（最稳定）===
from dare_framework.builder import Agent, AgentBuilder

# === 接口（稳定）===
# Kernel 接口
from dare_framework.interfaces import (
    IRunLoop,
    ILoopOrchestrator,
    IExecutionControl,
    IContextManager,
    IResourceManager,
    IEventLog,
    IToolGateway,
    ISecurityBoundary,
    IExtensionPoint,
)

# 组件接口
from dare_framework.interfaces import (
    IModelAdapter,
    IMemory,
    IRetriever,
    IPlanner,
    IValidator,
    IRemediator,
    ITool,
    ICapabilityProvider,
)

# === 类型（稳定）===
from dare_framework.types import (
    Task,
    Milestone,
    RunResult,
    Plan,
    Envelope,
    Budget,
    ToolResult,
)

# === 预设（稳定）===
from dare_framework.presets import (
    MinimalPreset,
    AutoGPTPreset,
    ReflexionPreset,
)

__all__ = [
    # Core
    "Agent", "AgentBuilder",
    # Kernel Interfaces
    "IRunLoop", "ILoopOrchestrator", "IExecutionControl",
    "IContextManager", "IResourceManager", "IEventLog",
    "IToolGateway", "ISecurityBoundary", "IExtensionPoint",
    # Component Interfaces
    "IModelAdapter", "IMemory", "IRetriever",
    "IPlanner", "IValidator", "IRemediator",
    "ITool", "ICapabilityProvider",
    # Types
    "Task", "Milestone", "RunResult", "Plan", "Envelope", "Budget", "ToolResult",
    # Presets
    "MinimalPreset", "AutoGPTPreset", "ReflexionPreset",
]

__version__ = "3.0.0"
```

#### 原则 2：三层 API 分级

```
┌─────────────────────────────────────────────────────────────┐
│ Level 1: Core API（最稳定）                                  │
│ from dare_framework import AgentBuilder, Agent              │
│ 承诺：Minor 版本绝不破坏                                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Level 2: Extended API（稳定）                                │
│ from dare_framework import IModelAdapter, IMemory           │
│ 承诺：弃用会提前一个 Minor 版本警告                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Level 3: Advanced API（可能变化）                            │
│ from dare_framework.advanced import ...                     │
│ 承诺：尽量保持稳定，但可能在 Minor 版本调整                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Level 4: Internal API（无承诺）                              │
│ from dare_framework._internal import ...                    │
│ 承诺：无稳定性承诺，随时可能变化                              │
└─────────────────────────────────────────────────────────────┘
```

#### 原则 3：内部实现隔离

```
dare_framework/
│
├── __init__.py          # 🔒 公开 API 门面
├── interfaces/          # 🔒 稳定的接口定义
│   ├── __init__.py     # 统一导出
│   ├── kernel.py       # 9 个 Kernel 接口
│   └── components.py   # 组件接口
├── types/               # 🔒 稳定的类型定义
├── presets/             # 🔒 稳定的预设
├── builder/             # 🔒 稳定的 Builder
│
└── _internal/           # ⚠️ 内部实现（可随时调整）
    ├── execution/
    ├── context/
    ├── security/
    ├── tool/
    ├── plan/
    └── model/
```

**关键**：用户代码永远不应该导入 `_internal` 下的任何东西

#### 原则 4：接口优先编程

**用户面向接口编程，不依赖具体实现**：

```python
# ✅ 正确：面向接口
from dare_framework import IModelAdapter, AgentBuilder

class MyCustomAdapter(IModelAdapter):
    """自定义模型适配器"""
    async def generate(self, messages, **kwargs):
        # 自定义实现
        ...

agent = AgentBuilder("my-agent").with_model(MyCustomAdapter()).build()

# ❌ 错误：依赖具体实现类
from dare_framework._internal.model.impl.openai import OpenAIAdapter  # 路径可能变化
```

#### 原则 5：弃用策略（Deprecation Policy）

```python
# 版本 3.1: 标记弃用，但仍然可用
import warnings

def old_method(self, arg):
    """旧方法（已弃用）"""
    warnings.warn(
        "old_method() is deprecated, use new_method() instead. "
        "Will be removed in version 4.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return self.new_method(arg)

# 版本 3.2: 继续保持弃用警告
# 版本 4.0: 移除旧方法
```

**弃用时间线**：
- Minor 版本 N：标记弃用 + 警告
- Minor 版本 N+1：继续警告
- Major 版本 M+1：移除

### 8.3 具体稳定性保证

#### Builder API 稳定性

```python
# 这些 API 是稳定承诺，不会在 minor 版本变化

agent = (
    AgentBuilder("my-agent")
    .with_model(model_adapter)      # ✅ 稳定
    .with_memory(memory)            # ✅ 稳定
    .with_tools(tool1, tool2)       # ✅ 稳定
    .with_planner(planner)          # ✅ 稳定
    .with_validator(validator)      # ✅ 稳定
    .with_preset(preset)            # ✅ 稳定
    .with_budget(budget)            # ✅ 稳定
    .build()                        # ✅ 稳定
)

result = await agent.run(task)      # ✅ 稳定
```

#### 接口签名稳定性

```python
# Kernel 接口签名是稳定承诺

class IModelAdapter(Protocol):
    """模型适配器接口 - 签名稳定"""

    async def generate(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        **kwargs,  # ← 通过 **kwargs 保留扩展空间
    ) -> ModelResponse:
        ...
```

**技巧**：使用 `**kwargs` 保留扩展空间，新参数可以作为 keyword-only 添加而不破坏兼容性

#### 返回类型稳定性

```python
# 返回类型使用 TypedDict 或 dataclass，便于扩展

@dataclass
class RunResult:
    """运行结果 - 字段只增不减"""
    success: bool
    output: Any
    errors: list[str]
    # 新版本可以添加字段，但不删除现有字段
    # v3.1 新增：
    # metrics: dict[str, Any] | None = None
```

### 8.4 Presets 作为缓冲层

**Presets 可以帮助用户隔离内部变化**：

```python
# 场景：内部组件重构了，但用户代码不需要改动

# 用户代码（不需要改）
from dare_framework import AgentBuilder, AutoGPTPreset

agent = AgentBuilder("my-agent").with_preset(AutoGPTPreset()).build()

# 框架内部（AutoGPTPreset 适配新组件）
class AutoGPTPreset(Preset):
    def configure(self, builder):
        # v3.0: 使用旧 Planner
        # return builder.with_planner(OldPlanner())

        # v3.1: 迁移到新 Planner（用户无感）
        return builder.with_planner(NewImprovedPlanner())
```

### 8.5 版本兼容矩阵

| 变更类型 | Minor 版本 | Major 版本 |
|---------|-----------|-----------|
| 添加新接口 | ✅ 允许 | ✅ 允许 |
| 添加新方法 | ✅ 允许（带默认值） | ✅ 允许 |
| 添加新参数 | ✅ 允许（keyword-only + 默认值） | ✅ 允许 |
| 修改参数类型 | ❌ 禁止 | ✅ 允许（需弃用周期） |
| 删除方法 | ❌ 禁止 | ✅ 允许（需弃用周期） |
| 修改返回类型 | ❌ 禁止 | ✅ 允许（需弃用周期） |
| 重命名模块路径 | ❌ 禁止（内部可以） | ✅ 允许 |

### 8.6 迁移指南模板

每次有破坏性变更时，提供清晰的迁移指南：

```markdown
# 从 v3.x 迁移到 v4.0

## Breaking Changes

### 1. IModelAdapter.generate() 签名变化

**v3.x**:
```python
async def generate(self, messages: list[Message]) -> str:
```

**v4.0**:
```python
async def generate(self, messages: list[Message]) -> ModelResponse:
```

**迁移方法**:
```python
# 旧代码
result = await adapter.generate(messages)
print(result)  # 直接是字符串

# 新代码
result = await adapter.generate(messages)
print(result.content)  # 从 ModelResponse 获取内容
```
```

### 8.7 完整的 v3 目录结构（带稳定性标记）

```
dare_framework/
│
├── __init__.py              # 🔒 Level 1: 公开 API 门面
│
├── interfaces/              # 🔒 Level 2: 稳定接口
│   ├── __init__.py         # 统一导出
│   ├── kernel.py           # Kernel 接口（最稳定）
│   └── components.py       # 组件接口
│
├── types/                   # 🔒 Level 2: 稳定类型
│   ├── __init__.py
│   ├── core.py             # Task, Plan, Envelope
│   └── results.py          # RunResult, ToolResult
│
├── presets/                 # 🔒 Level 2: 稳定预设
│   ├── __init__.py
│   ├── base.py
│   ├── minimal.py
│   ├── autogpt.py
│   └── reflexion.py
│
├── builder/                 # 🔒 Level 1: 稳定 Builder
│   ├── __init__.py
│   ├── agent.py
│   └── builder.py
│
├── advanced/                # ⚠️ Level 3: 高级 API（可能变化）
│   ├── __init__.py
│   ├── custom_loop.py      # 自定义循环
│   └── low_level.py        # 低层 API
│
└── _internal/               # 🚫 Level 4: 内部实现（无稳定承诺）
    ├── execution/
    │   ├── kernel.py
    │   ├── types.py
    │   └── impl/
    ├── context/
    │   ├── kernel.py
    │   ├── components.py
    │   ├── types.py
    │   └── impl/
    ├── security/
    │   ├── kernel.py
    │   ├── components.py
    │   ├── types.py
    │   └── impl/
    ├── tool/
    │   ├── kernel.py
    │   ├── components.py
    │   ├── types.py
    │   └── impl/
    ├── plan/
    │   ├── components.py
    │   ├── types.py
    │   └── impl/
    ├── model/
    │   ├── components.py
    │   ├── types.py
    │   └── impl/
    └── protocols/
        └── ...
```

### 8.8 用户使用示例

```python
"""
示例：用户代码只依赖稳定 API
即使框架内部重构，这段代码也不需要改动
"""

# ✅ 只从顶级包导入（稳定）
from dare_framework import (
    AgentBuilder,
    AutoGPTPreset,
    IModelAdapter,
    Task,
    RunResult,
)

# ✅ 面向接口实现自定义组件
class MyModelAdapter(IModelAdapter):
    async def generate(self, messages, **kwargs):
        # 自定义实现
        return ModelResponse(content="Hello!")

# ✅ 使用 Builder 和 Preset
agent = (
    AgentBuilder("my-agent")
    .with_preset(AutoGPTPreset())
    .with_model(MyModelAdapter())
    .build()
)

# ✅ 运行
result: RunResult = await agent.run(Task(goal="Do something"))
print(result.success)
```

**关键保证**：
- 上面这段代码在 v3.0、v3.1、v3.2... 都能正常工作
- 只有在 v4.0 才可能需要修改，且会提前弃用警告

---

## 九、总结

### v3 的核心价值

1. **功能域垂直切分**（继承 v2）
2. **Kernel 边界清晰**（修正 v2）
3. **Context Engineering 完整**（修正 v2）
4. **Security 独立**（修正 v2）
5. **乐高式组合**（新增）
6. **API 稳定性设计**（新增）- 用户无感升级

### 稳定性承诺

| 层级 | 导入方式 | 稳定性承诺 |
|-----|---------|-----------|
| Level 1 | `from dare_framework import AgentBuilder` | 最稳定，Minor 版本绝不破坏 |
| Level 2 | `from dare_framework import IModelAdapter` | 稳定，弃用会提前警告 |
| Level 3 | `from dare_framework.advanced import ...` | 可能变化，尽量保持稳定 |
| Level 4 | `from dare_framework._internal import ...` | 无承诺，随时可能变化 |

### 最终建议

**框架开发者**：
1. 严格遵守 Package Facade Pattern
2. 内部实现放在 `_internal/` 下
3. 所有公开 API 通过顶级 `__init__.py` 导出
4. 遵循弃用策略，给用户迁移时间

**框架用户**：
1. 只从顶级包导入
2. 面向接口编程
3. 使用 Presets 隔离内部变化
4. 注意弃用警告，及时迁移

---

**参考文档**：
- [Architecture_Final_Review_v2.1.md](./design/Architecture_Final_Review_v2.1.md) - DARE 架构规范
