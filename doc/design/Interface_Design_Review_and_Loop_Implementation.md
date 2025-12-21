# 接口设计评审与循环实现验证

> 本文档综合 AgentScope 和 Pydantic AI 的对比分析，验证接口设计是否能支持三层循环模型的实现。

---

## 一、框架对比综合评审

### 1.1 对比总览

| 维度 | AgentScope | Pydantic AI | DARE Framework |
|-----|-----------|-------------|----------------|
| **核心哲学** | 通用多模态智能体 | FastAPI 体验、类型安全 | 工业级安全、可审计 |
| **类型安全** | ⭐⭐ 一般 | ⭐⭐⭐⭐⭐ 极强 | ⭐⭐⭐ 待加强 |
| **扩展性** | ⭐⭐⭐⭐ 良好 | ⭐⭐⭐⭐ 良好 | ⭐⭐⭐⭐ 良好 |
| **安全性** | ⭐⭐ 弱 | ⭐⭐ 弱 | ⭐⭐⭐⭐⭐ 核心特性 |
| **可审计** | ⭐⭐ StateModule | ⭐⭐⭐ Durable Execution | ⭐⭐⭐⭐⭐ EventLog + Hash Chain |
| **MCP 支持** | ⭐⭐⭐⭐ 有 | ⭐⭐ 有限 | ⭐⭐⭐⭐ 待实现 |
| **依赖注入** | ⭐⭐ 无 | ⭐⭐⭐⭐⭐ RunContext[T] | ⭐⭐ 待加强 |

### 1.2 应该学习的设计（按优先级）

#### P0 - 必须采纳

| 来源 | 设计 | 采纳理由 | 影响的接口 |
|-----|------|---------|-----------|
| Pydantic AI | `RunContext[DepsT]` 泛型依赖注入 | 类型安全、测试友好、IDE 支持 | `ExecutionContext` → 重构为泛型 |
| Pydantic AI | `Agent[DepsT, OutputT]` 泛型 Agent | 编译时输出类型检查 | `IAgent` → 添加泛型参数 |
| Pydantic AI | 结构化输出 `output_type: BaseModel` | LLM 输出可验证 | `IRuntime.run()` → 返回类型化结果 |

#### P1 - 应该采纳

| 来源 | 设计 | 采纳理由 | 影响的接口 |
|-----|------|---------|-----------|
| Pydantic AI | `IStreamedResponse` 流式响应 | 支持流式输出、实时反馈 | 新增接口 |
| Pydantic AI | Toolset 增强（`id`, `filter`, `prefix`） | 工具管理更灵活 | `IToolkit` → 增强 |
| AgentScope | `StateModule` 嵌套状态 | 嵌套组件状态自动序列化 | `ICheckpoint` → 增强 |
| AgentScope | 工具分组管理 | 按场景激活/禁用工具组 | `IToolkit` → 增强 |

#### P2 - 可选采纳

| 来源 | 设计 | 说明 |
|-----|------|------|
| Pydantic AI | `IUIAdapter` | UI 协议适配，非核心 |
| AgentScope | Evaluator 系统 | 评估框架，后期可加 |
| AgentScope | KnowledgeBase | RAG 能力，可用 Memory 覆盖 |

### 1.3 必须保持的差异化设计

| DARE 特有设计 | 为什么保持 | 其他框架的问题 |
|-------------|----------|--------------|
| **信任边界** `TrustBoundary` | 安全核心，LLM 输出不可信 | 其他框架直接信任 LLM 输出 |
| **审计日志** `EventLog` | 金融级合规，hash chain 防篡改 | 其他框架仅做状态恢复 |
| **工具风险级别** `ToolRiskLevel` | 分级管控，高危需审批 | 其他框架无风险分类 |
| **策略引擎** `IPolicyEngine` | 权限控制，策略即代码 | 其他框架无策略层 |
| **验证闭环** 五个可验证闭环 | 每个安全机制都可证明 | 其他框架无验证闭环 |

### 1.4 接口融合建议

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       DARE Framework v2 接口层                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Layer 1: Core Infrastructure（DARE 核心 - 保持）                        │
│  ───────────────────────────────────────────────                        │
│  IRuntime, IEventLog, IToolRuntime, IPolicyEngine                       │
│  TrustBoundary, IContextAssembler                                       │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Layer 2: Type-Safe Abstractions（← 学习自 Pydantic AI）                 │
│  ───────────────────────────────────────────────────                    │
│  RunContext[DepsT]          泛型依赖注入上下文                           │
│  Agent[DepsT, OutputT]      泛型 Agent 定义                             │
│  RunResult[OutputT]         泛型运行结果                                 │
│  IStreamedResponse[T]       流式响应接口                                 │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Layer 3: Pluggable Components（保持 + 增强）                            │
│  ───────────────────────────────────────────────                        │
│  IModelAdapter, IToolkit(增强), IMCPClient                              │
│  IMemory, ISkill, IHook, ICheckpoint(增强)                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、接口与循环模型的映射验证

### 2.1 循环模型回顾

```
三层循环模型：

Session Loop（跨 Context Window）
    └── Milestone Loop（Plan → Validate → Execute → Verify）
            └── Tool Loop（Gather → Act → Check → Update）
```

### 2.2 接口覆盖度检查

| 循环层级 | 循环职责 | 需要的能力 | 对应接口 | 覆盖状态 |
|---------|---------|-----------|---------|---------|
| **Session Loop** | 跨 session 状态保持 | 状态持久化 | `ICheckpoint` | ⚠️ 需增强 |
| | 长任务续跑 | 恢复执行 | `IRuntime.resume()` | ✅ 有 |
| | 进度追踪 | 事件日志 | `IEventLog` | ✅ 有 |
| **Milestone Loop** | Observe（观察） | 上下文装配 | `IContextAssembler` | ✅ 有 |
| | Plan（规划） | LLM 调用 | `IModelAdapter.generate()` | ✅ 有 |
| | Validate（验证） | 策略检查 | `IPolicyEngine.check()` | ✅ 有 |
| | Execute（执行） | 步骤执行 | `IToolRuntime.invoke()` | ✅ 有 |
| | Verify（验收） | 完成验证 | `DonePredicate` | ⚠️ 需完善 |
| **Tool Loop** | Gather（收集） | 上下文获取 | `IMemory`, `IContextAssembler` | ✅ 有 |
| | Act（执行） | 工具调用 | `IToolRuntime.invoke()` | ✅ 有 |
| | Check（检查） | 门禁检查 | `IToolRuntime` (内置) | ✅ 有 |
| | Update（更新） | 证据收集 | `IEventLog.append()` | ✅ 有 |

### 2.3 缺失或需要补充的接口

| 缺失点 | 说明 | 建议的接口 |
|-------|------|-----------|
| `Envelope` 数据结构 | WorkUnit 的执行边界 | 添加 `@dataclass Envelope` |
| `DonePredicate` 接口 | 完成条件定义 | 添加 `IDonePredicate` 接口 |
| `ValidatedStep` 数据结构 | 验证后的步骤 | 添加 `@dataclass ValidatedStep` |
| 预算管理 | Budget 追踪 | 添加 `IBudgetTracker` 或嵌入 `ExecutionContext` |
| 停滞检测 | 连续失败检测 | 添加到 `DonePredicate` 逻辑中 |

---

## 三、循环实现伪代码

### 3.1 数据结构补充

```python
from dataclasses import dataclass
from typing import Generic, TypeVar, Any
from enum import Enum
from pydantic import BaseModel

# === 泛型类型 ===
DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT", bound=BaseModel)


# === 步骤类型 ===
class StepType(Enum):
    ATOMIC = "atomic"        # 单次工具调用
    WORK_UNIT = "work_unit"  # 多次迭代


# === Envelope（执行边界）===
@dataclass
class Envelope:
    """WorkUnit 的执行边界，由 Validate 阶段生成"""
    allowed_tools: list[str]           # 允许调用的工具
    required_evidence: list[str]       # 必须产出的证据
    budget: "Budget"                   # 预算限制
    risk_level: ToolRiskLevel          # 最高风险级别（派生自 allowed_tools）


@dataclass
class Budget:
    """预算定义"""
    max_tool_calls: int = 30
    max_tokens: int = 50000
    max_wall_time_seconds: int = 180
    max_stagnant_iterations: int = 3


# === DonePredicate（完成条件）===
@dataclass
class DonePredicate:
    """完成条件定义"""
    evidence_conditions: list[dict]    # 必须满足的证据条件
    invariant_conditions: list[dict]   # 不变量条件（lint_pass, compile_pass）
    require_all: bool = True           # 是否需要全部满足

    def is_satisfied(self, collected_evidence: list[str]) -> bool:
        """检查是否满足完成条件"""
        if self.require_all:
            return all(
                self._check_condition(cond, collected_evidence)
                for cond in self.evidence_conditions
            )
        return any(
            self._check_condition(cond, collected_evidence)
            for cond in self.evidence_conditions
        )

    def _check_condition(self, condition: dict, evidence: list[str]) -> bool:
        """检查单个条件"""
        cond_type = condition.get("type")
        if cond_type == "test_pass":
            return any("test_pass" in e for e in evidence)
        if cond_type == "file_modified":
            return any("file_modified" in e for e in evidence)
        return False


# === ValidatedStep（验证后的步骤）===
@dataclass
class ValidatedStep:
    """经过 Validate 阶段验证的步骤"""
    step_id: str
    step_type: StepType
    description: str

    # Atomic Step 字段
    tool_name: str | None = None
    tool_input: dict | None = None

    # WorkUnit Step 字段
    skill_name: str | None = None
    skill_input: dict | None = None
    envelope: Envelope | None = None
    done_predicate: DonePredicate | None = None

    # 执行状态
    status: str = "pending"  # pending | in_progress | done | failed


# === 运行上下文（融合 Pydantic AI 的依赖注入）===
@dataclass
class RunContext(Generic[DepsT]):
    """
    运行上下文（学习自 Pydantic AI）
    提供类型安全的依赖注入
    """
    # 依赖注入
    deps: DepsT

    # 运行标识
    run_id: str
    session_id: str
    milestone_id: str
    step_id: str

    # DARE 特有：信任信息
    trust_level: TrustLevel
    agent_id: str

    # 预算追踪
    budget_used: Budget
    budget_limit: Budget

    # 收集的证据
    collected_evidence: list[str]

    # 服务引用（框架注入）
    event_log: IEventLog
    tool_runtime: IToolRuntime
    policy_engine: IPolicyEngine
    model_adapter: IModelAdapter


# === 运行结果（泛型化）===
@dataclass
class RunResult(Generic[OutputT]):
    """泛型运行结果"""
    success: bool
    output: OutputT | None
    evidence: list[str]
    events: list[str]  # event_id 列表
    error: str | None = None
```

### 3.2 Session Loop 伪代码

```python
class SessionLoop:
    """
    第一层循环：跨 Context Window
    职责：长任务不断片，跨 session 保持状态
    """

    def __init__(
        self,
        runtime: IRuntime,
        event_log: IEventLog,
        checkpoint: ICheckpoint,
    ):
        self.runtime = runtime
        self.event_log = event_log
        self.checkpoint = checkpoint

    async def run(
        self,
        task: Task,
        ctx: RunContext[DepsT],
    ) -> RunResult[OutputT]:
        """执行长任务"""

        # 1. 检查是否有可恢复的 checkpoint
        checkpoint = await self.checkpoint.load(task.task_id)
        if checkpoint:
            # 从 checkpoint 恢复状态
            milestones = checkpoint.remaining_milestones
            progress = checkpoint.progress
        else:
            # 初始化任务
            milestones = await self._plan_milestones(task, ctx)
            progress = TaskProgress(task_id=task.task_id)

        # 2. 记录 session 开始
        await self.event_log.append(Event(
            event_type="session_start",
            run_id=ctx.run_id,
            session_id=ctx.session_id,
            payload={"task_id": task.task_id, "milestone_count": len(milestones)},
        ))

        # 3. 逐个执行 Milestone
        for milestone in milestones:
            try:
                # 执行 Milestone Loop
                milestone_result = await MilestoneLoop(
                    runtime=self.runtime,
                    event_log=self.event_log,
                ).run(milestone, ctx)

                # 更新进度
                progress.completed_milestones.append(milestone.milestone_id)

                # 保存 checkpoint（断点续跑）
                await self.checkpoint.save(CheckpointState(
                    task_id=task.task_id,
                    remaining_milestones=[m for m in milestones if m.milestone_id not in progress.completed_milestones],
                    progress=progress,
                ))

                if not milestone_result.success:
                    # Milestone 失败，根据策略决定是否继续
                    if milestone.is_critical:
                        return RunResult(
                            success=False,
                            output=None,
                            evidence=progress.evidence,
                            events=progress.events,
                            error=f"Critical milestone failed: {milestone.milestone_id}",
                        )

            except ContextWindowExceeded:
                # Context 窗口满了，保存状态，结束本 session
                await self.checkpoint.save(CheckpointState(
                    task_id=task.task_id,
                    remaining_milestones=[m for m in milestones if m.milestone_id not in progress.completed_milestones],
                    progress=progress,
                    reason="context_window_exceeded",
                ))
                raise  # 让上层处理

        # 4. 任务完成
        await self.event_log.append(Event(
            event_type="session_end",
            run_id=ctx.run_id,
            session_id=ctx.session_id,
            payload={"status": "completed"},
        ))

        return RunResult(
            success=True,
            output=progress.final_output,
            evidence=progress.evidence,
            events=progress.events,
        )

    async def _plan_milestones(self, task: Task, ctx: RunContext) -> list[Milestone]:
        """规划 Milestones（调用 LLM）"""
        # LLM 输出不可信，需要经过 Validate
        response = await ctx.model_adapter.generate(
            messages=[
                {"role": "system", "content": "You are a task planner..."},
                {"role": "user", "content": f"Plan milestones for: {task.description}"},
            ],
            tools=None,  # 规划阶段不需要工具
        )

        # 解析并验证 milestones
        milestones = self._parse_milestones(response.content)
        return milestones
```

### 3.3 Milestone Loop 伪代码

```python
class MilestoneLoop:
    """
    第二层循环：单个里程碑
    职责：可控、可审计、可验收
    流程：Observe → Plan → Validate → Execute → Verify
    """

    def __init__(
        self,
        runtime: IRuntime,
        event_log: IEventLog,
        policy_engine: IPolicyEngine,
        tool_runtime: IToolRuntime,
        model_adapter: IModelAdapter,
    ):
        self.runtime = runtime
        self.event_log = event_log
        self.policy_engine = policy_engine
        self.tool_runtime = tool_runtime
        self.model_adapter = model_adapter

    async def run(
        self,
        milestone: Milestone,
        ctx: RunContext[DepsT],
    ) -> MilestoneResult:
        """执行单个 Milestone"""

        max_replan_attempts = 3
        attempt = 0

        while attempt < max_replan_attempts:
            attempt += 1

            # === Phase 1: Observe ===
            context = await self._observe(milestone, ctx)

            # === Phase 2: Plan (LLM, 不可信) ===
            proposed_steps = await self._plan(milestone, context, ctx)

            # === Phase 3: Validate (系统, 可信) ===
            validated_steps = await self._validate(proposed_steps, ctx)

            if not validated_steps:
                # 验证失败，无法执行
                await self.event_log.append(Event(
                    event_type="milestone_validation_failed",
                    milestone_id=milestone.milestone_id,
                    payload={"reason": "no_valid_steps"},
                ))
                continue  # 重新规划

            # === Phase 4: Execute ===
            execute_result = await self._execute(validated_steps, ctx)

            # === Phase 5: Verify ===
            verify_result = await self._verify(milestone, execute_result, ctx)

            if verify_result.passed:
                return MilestoneResult(
                    success=True,
                    evidence=execute_result.evidence,
                    steps_executed=len(validated_steps),
                )
            else:
                # 验证失败，尝试 Remediate
                if await self._should_remediate(verify_result, ctx):
                    # 反思并重新规划
                    reflection = await self._reflect(verify_result, ctx)
                    ctx.deps.lessons_learned.append(reflection)
                    continue  # 回到 Plan
                else:
                    return MilestoneResult(
                        success=False,
                        error=verify_result.failure_reason,
                    )

        return MilestoneResult(
            success=False,
            error=f"Max replan attempts ({max_replan_attempts}) exceeded",
        )

    async def _observe(self, milestone: Milestone, ctx: RunContext) -> Context:
        """
        Observe 阶段：收集上下文
        """
        # 获取相关记忆
        memory_context = ""
        if ctx.deps.memory:
            memory_context = await ctx.deps.memory.get_relevant_context(
                task=milestone.description,
                budget_tokens=2000,
            )

        # 装配上下文
        return Context(
            milestone=milestone,
            memory=memory_context,
            available_tools=self.tool_runtime.list_tools(),
            available_skills=ctx.deps.skills,
            collected_evidence=ctx.collected_evidence,
        )

    async def _plan(
        self,
        milestone: Milestone,
        context: Context,
        ctx: RunContext,
    ) -> list[ProposedStep]:
        """
        Plan 阶段：LLM 规划步骤（输出不可信！）
        """
        response = await self.model_adapter.generate(
            messages=[
                {"role": "system", "content": self._build_planner_prompt(context)},
                {"role": "user", "content": f"Plan steps to achieve: {milestone.description}"},
            ],
            tools=context.available_tools,
        )

        # 解析 LLM 输出为 ProposedStep（不可信）
        proposed_steps = self._parse_proposed_steps(response)
        return proposed_steps

    async def _validate(
        self,
        proposed_steps: list[ProposedStep],
        ctx: RunContext,
    ) -> list[ValidatedStep]:
        """
        Validate 阶段：系统验证（制定契约）

        这里是信任边界！
        - proposed_steps 来自 LLM，不可信
        - validated_steps 是系统验证后的，可信
        """
        validated = []

        for step in proposed_steps:
            # Gate 1: 检查工具/技能是否存在
            if step.step_type == StepType.ATOMIC:
                tool = self.tool_runtime.get_tool(step.tool_name)
                if not tool:
                    await self.event_log.append(Event(
                        event_type="validation_rejected",
                        payload={"reason": f"Tool not found: {step.tool_name}"},
                    ))
                    continue

                # Gate 2: 检查策略
                policy_result = await self.policy_engine.check(
                    action="invoke_tool",
                    resource=step.tool_name,
                    context=ctx,
                )
                if not policy_result.allowed:
                    await self.event_log.append(Event(
                        event_type="validation_rejected",
                        payload={"reason": f"Policy denied: {policy_result.reason}"},
                    ))
                    continue

                # Gate 3: 从 Registry 派生安全字段（不信任 LLM 提供的）
                validated.append(ValidatedStep(
                    step_id=generate_id(),
                    step_type=StepType.ATOMIC,
                    description=step.description,
                    tool_name=step.tool_name,
                    tool_input=step.tool_input,
                    # 安全关键字段从 Registry 派生，不是从 LLM 输出
                    # risk_level=tool.risk_level,  # 从 Registry 获取
                    # timeout=tool.timeout_seconds,  # 从 Registry 获取
                ))

            elif step.step_type == StepType.WORK_UNIT:
                skill = self._get_skill(step.skill_name, ctx)
                if not skill:
                    continue

                # 生成 Envelope（执行边界）
                envelope = Envelope(
                    allowed_tools=skill.required_tools,
                    required_evidence=step.required_evidence,
                    budget=Budget(
                        max_tool_calls=30,
                        max_wall_time_seconds=180,
                    ),
                    risk_level=self._derive_risk_level(skill.required_tools),
                )

                # 生成 DonePredicate
                done_predicate = skill.done_predicate

                validated.append(ValidatedStep(
                    step_id=generate_id(),
                    step_type=StepType.WORK_UNIT,
                    description=step.description,
                    skill_name=step.skill_name,
                    skill_input=step.skill_input,
                    envelope=envelope,
                    done_predicate=done_predicate,
                ))

        return validated

    async def _execute(
        self,
        validated_steps: list[ValidatedStep],
        ctx: RunContext,
    ) -> ExecuteResult:
        """
        Execute 阶段：执行验证后的步骤
        """
        evidence = []

        for step in validated_steps:
            step.status = "in_progress"

            if step.step_type == StepType.ATOMIC:
                # 直接调用工具，不需要 Tool Loop
                result = await self.tool_runtime.invoke(
                    tool_name=step.tool_name,
                    input=step.tool_input,
                    context=ctx,
                )

                step.status = "done" if result.success else "failed"
                if result.evidence_ref:
                    evidence.append(result.evidence_ref)

            elif step.step_type == StepType.WORK_UNIT:
                # 进入 Tool Loop
                tool_loop_result = await ToolLoop(
                    tool_runtime=self.tool_runtime,
                    model_adapter=self.model_adapter,
                    event_log=self.event_log,
                ).run(
                    step=step,
                    envelope=step.envelope,
                    done_predicate=step.done_predicate,
                    ctx=ctx,
                )

                step.status = "done" if tool_loop_result.success else "failed"
                evidence.extend(tool_loop_result.evidence)

        return ExecuteResult(
            success=all(s.status == "done" for s in validated_steps),
            evidence=evidence,
            steps=validated_steps,
        )

    async def _verify(
        self,
        milestone: Milestone,
        execute_result: ExecuteResult,
        ctx: RunContext,
    ) -> VerifyResult:
        """
        Verify 阶段：确定性验收
        """
        # 检查里程碑的完成条件
        all_evidence_met = all(
            req in execute_result.evidence
            for req in milestone.required_evidence
        )

        # 运行验证器（如果有）
        if milestone.verifier:
            verifier_result = await milestone.verifier.verify(
                execute_result,
                ctx,
            )
            return VerifyResult(
                passed=verifier_result.passed and all_evidence_met,
                failure_reason=verifier_result.failure_reason,
            )

        return VerifyResult(
            passed=all_evidence_met,
            failure_reason=None if all_evidence_met else "Missing required evidence",
        )

    async def _reflect(self, verify_result: VerifyResult, ctx: RunContext) -> str:
        """反思失败原因（可选，用于 Remediate）"""
        response = await self.model_adapter.generate(
            messages=[
                {"role": "system", "content": "Analyze why the task failed and suggest improvements."},
                {"role": "user", "content": f"Failure reason: {verify_result.failure_reason}"},
            ],
        )
        return response.content
```

### 3.4 Tool Loop 伪代码

```python
class ToolLoop:
    """
    第三层循环：WorkUnit 内部
    职责：高效迭代，轻量门禁
    流程：Gather → Act → Check → Update (循环直到 DonePredicate 满足)
    """

    def __init__(
        self,
        tool_runtime: IToolRuntime,
        model_adapter: IModelAdapter,
        event_log: IEventLog,
    ):
        self.tool_runtime = tool_runtime
        self.model_adapter = model_adapter
        self.event_log = event_log

    async def run(
        self,
        step: ValidatedStep,
        envelope: Envelope,
        done_predicate: DonePredicate,
        ctx: RunContext[DepsT],
    ) -> ToolLoopResult:
        """执行 Tool Loop"""

        evidence = []
        iteration = 0
        stagnant_count = 0
        last_evidence_count = 0

        # 初始化预算追踪
        budget_tracker = BudgetTracker(envelope.budget)

        await self.event_log.append(Event(
            event_type="tool_loop_start",
            step_id=step.step_id,
            payload={"envelope": envelope.__dict__},
        ))

        while True:
            iteration += 1

            # === 检查终止条件 ===

            # 条件 1: DonePredicate 满足
            if done_predicate.is_satisfied(evidence):
                await self.event_log.append(Event(
                    event_type="tool_loop_end",
                    step_id=step.step_id,
                    payload={"reason": "done_predicate_satisfied", "iterations": iteration},
                ))
                return ToolLoopResult(success=True, evidence=evidence)

            # 条件 2: 预算耗尽
            if budget_tracker.is_exceeded():
                await self.event_log.append(Event(
                    event_type="tool_loop_end",
                    step_id=step.step_id,
                    payload={"reason": "budget_exceeded", "iterations": iteration},
                ))
                return ToolLoopResult(success=False, evidence=evidence, error="Budget exceeded")

            # 条件 3: 停滞检测
            if len(evidence) == last_evidence_count:
                stagnant_count += 1
            else:
                stagnant_count = 0
                last_evidence_count = len(evidence)

            if stagnant_count >= envelope.budget.max_stagnant_iterations:
                await self.event_log.append(Event(
                    event_type="tool_loop_end",
                    step_id=step.step_id,
                    payload={"reason": "stagnant", "iterations": iteration},
                ))
                return ToolLoopResult(success=False, evidence=evidence, error="Stagnant detected")

            # === Gather: 收集当前上下文 ===
            gather_context = await self._gather(step, evidence, ctx)

            # === Act: LLM 决定下一步动作 ===
            action = await self._decide_action(
                gather_context,
                envelope.allowed_tools,  # 只能从允许的工具中选择
                ctx,
            )

            if action is None:
                # LLM 认为已完成或无法继续
                break

            # === Check: 门禁检查 ===
            # ToolRuntime Gate 检查 allowed_tools
            if action.tool_name not in envelope.allowed_tools:
                # 越界！Policy Deny
                await self.event_log.append(Event(
                    event_type="tool_denied",
                    step_id=step.step_id,
                    payload={
                        "tool": action.tool_name,
                        "reason": "not_in_allowed_tools",
                        "allowed": envelope.allowed_tools,
                    },
                ))
                continue  # 跳过这个动作，让 LLM 重新决定

            # === 执行工具 ===
            result = await self.tool_runtime.invoke(
                tool_name=action.tool_name,
                input=action.tool_input,
                context=ctx,
                # 传入 envelope 用于额外检查
                envelope=envelope,
            )

            # 更新预算
            budget_tracker.record_tool_call()

            # === Update: 更新证据 ===
            if result.success and result.evidence_ref:
                evidence.append(result.evidence_ref)
                ctx.collected_evidence.append(result.evidence_ref)

            await self.event_log.append(Event(
                event_type="tool_executed",
                step_id=step.step_id,
                payload={
                    "tool": action.tool_name,
                    "success": result.success,
                    "evidence": result.evidence_ref,
                    "iteration": iteration,
                },
            ))

        # 循环正常结束
        return ToolLoopResult(
            success=done_predicate.is_satisfied(evidence),
            evidence=evidence,
        )

    async def _gather(
        self,
        step: ValidatedStep,
        collected_evidence: list[str],
        ctx: RunContext,
    ) -> GatherContext:
        """Gather 阶段：收集上下文"""
        return GatherContext(
            step_description=step.description,
            skill_input=step.skill_input,
            collected_evidence=collected_evidence,
            iteration_count=len(collected_evidence),
        )

    async def _decide_action(
        self,
        gather_context: GatherContext,
        allowed_tools: list[str],
        ctx: RunContext,
    ) -> ToolAction | None:
        """
        决定下一步动作（调用 LLM）

        注意：LLM 只能从 allowed_tools 中选择
        """
        # 构建工具定义（只包含允许的工具）
        tools = [
            self.tool_runtime.get_tool(name).to_definition()
            for name in allowed_tools
        ]

        response = await ctx.model_adapter.generate(
            messages=[
                {
                    "role": "system",
                    "content": f"You are working on: {gather_context.step_description}. "
                               f"You have collected evidence: {gather_context.collected_evidence}. "
                               "Decide the next action to take.",
                },
            ],
            tools=tools,
        )

        if response.tool_calls:
            call = response.tool_calls[0]
            return ToolAction(
                tool_name=call.name,
                tool_input=call.arguments,
            )

        return None  # LLM 认为已完成


@dataclass
class ToolLoopResult:
    """Tool Loop 结果"""
    success: bool
    evidence: list[str]
    error: str | None = None


class BudgetTracker:
    """预算追踪器"""

    def __init__(self, budget: Budget):
        self.budget = budget
        self.tool_calls = 0
        self.start_time = time.time()

    def record_tool_call(self):
        self.tool_calls += 1

    def is_exceeded(self) -> bool:
        if self.tool_calls >= self.budget.max_tool_calls:
            return True
        if time.time() - self.start_time >= self.budget.max_wall_time_seconds:
            return True
        return False
```

---

## 四、接口设计验证结论

### 4.1 接口覆盖度总结

| 循环层级 | 核心需求 | 接口覆盖 | 状态 |
|---------|---------|---------|------|
| Session Loop | 跨 session 恢复 | `ICheckpoint`, `IRuntime.resume()` | ✅ 充分 |
| Session Loop | 进度持久化 | `IEventLog` | ✅ 充分 |
| Milestone Loop | 上下文装配 | `IContextAssembler` | ✅ 充分 |
| Milestone Loop | LLM 规划 | `IModelAdapter.generate()` | ✅ 充分 |
| Milestone Loop | 策略验证 | `IPolicyEngine.check()` | ✅ 充分 |
| Milestone Loop | 步骤执行 | `IToolRuntime.invoke()` | ✅ 充分 |
| Milestone Loop | 完成验证 | 需补充 `DonePredicate` 接口 | ⚠️ 需补充 |
| Tool Loop | 工具门禁 | `IToolRuntime` + `Envelope` | ✅ 充分 |
| Tool Loop | 预算管理 | 需补充 `Budget` + `BudgetTracker` | ⚠️ 需补充 |
| Tool Loop | 停滞检测 | 逻辑内置于 `ToolLoop` | ✅ 充分 |

### 4.2 需要补充的数据结构

```python
# 已在本文档第三节定义，需要正式加入框架：

1. Envelope          # WorkUnit 执行边界
2. Budget            # 预算定义
3. DonePredicate     # 完成条件
4. ValidatedStep     # 验证后的步骤
5. BudgetTracker     # 预算追踪器
```

### 4.3 需要增强的接口

| 接口 | 增强内容 | 来源 |
|-----|---------|------|
| `ExecutionContext` | 改为泛型 `RunContext[DepsT]` | Pydantic AI |
| `IAgent` | 改为泛型 `IAgent[DepsT, OutputT]` | Pydantic AI |
| `IToolkit` | 添加 `id`, `filter()`, `prefix()` | Pydantic AI + AgentScope |
| `ICheckpoint` | 支持嵌套状态序列化 | AgentScope |

### 4.4 结论

**接口设计基本能够支持三层循环模型的实现**，但需要：

1. **补充数据结构**：`Envelope`, `Budget`, `DonePredicate`, `ValidatedStep`
2. **增强类型安全**：采纳 Pydantic AI 的泛型依赖注入模式
3. **增强工具管理**：采纳 Pydantic AI 和 AgentScope 的工具集增强

---

*文档状态：接口设计评审完成，循环实现伪代码已验证*
