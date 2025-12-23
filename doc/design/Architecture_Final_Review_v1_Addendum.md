# 架构终稿评审 v1 - 补充说明

> 补充架构终稿遗漏的关键设计点，整合 Loop Model v2.2 的核心概念

---

## 一、核心概念（一句话版）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  宏观 Validate = 制定契约（这件事允许做什么、需要什么证据、风险怎么控）          │
│  ToolRuntime Gate = 执行契约（每一步都检查你有没有作弊）                         │
│  Done Predicate = 结束条件（什么时候算完成）                                     │
│  Plan Loop = 生成有效计划（失败的计划不污染外层上下文）                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、Step 类型详解

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  Step 分类                                                                       │
│  ═════════                                                                       │
│                                                                                 │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │ ATOMIC STEP                     │  │ WORKUNIT STEP (ITERATIVE)           │  │
│  │ ─────────────                   │  │ ──────────────                      │  │
│  │                                 │  │                                     │  │
│  │ 定义：一次调用完成              │  │ 定义：需要多次迭代                  │  │
│  │                                 │  │                                     │  │
│  │ 例子：                          │  │ 例子：                              │  │
│  │ • read_file(path)              │  │ • FixFailingTest(suite)            │  │
│  │ • grep(pattern)                │  │ • ImplementFeature(spec)           │  │
│  │ • run_tests(suite)             │  │ • RefactorModule(path)             │  │
│  │ • apply_patch(patch)           │  │                                     │  │
│  │                                 │  │                                     │  │
│  │ 结束：工具返回                  │  │ 结束：DonePredicate 满足            │  │
│  │                                 │  │                                     │  │
│  │ Tool Loop：不需要               │  │ Tool Loop：需要                     │  │
│  │                                 │  │                                     │  │
│  └─────────────────────────────────┘  └─────────────────────────────────────┘  │
│                                                                                 │
│  谁决定？                                                                        │
│  ─────────                                                                       │
│  LLM 在 Plan 时选择：                                                            │
│  • 用具体 tool → Atomic Step                                                    │
│  • 用 registered skill → WorkUnit Step                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2.5 Plan Loop（计划生成循环）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  Plan Loop = Milestone Loop 的内层循环                                          │
│  ══════════════════════════════════════                                         │
│                                                                                 │
│  职责：生成一个有效的、通过 Validate 的计划                                      │
│  ────────────────────────────────────────                                       │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                         │   │
│  │  while not plan_budget.exceeded():                                      │   │
│  │                                                                         │   │
│  │      ┌──────────┐   ┌──────────┐   ┌──────────┐                        │   │
│  │      │ Observe  │──▶│   Plan   │──▶│ Validate │                        │   │
│  │      └──────────┘   └──────────┘   └────┬─────┘                        │   │
│  │           ▲                              │                              │   │
│  │           │                              ├─▶ ✓ 成功 → return           │   │
│  │           │         plan_attempts        │             ValidatedPlan    │   │
│  │           │         (临时变量)            │                              │   │
│  │           │                              └─▶ ✗ 失败 → 记录并 continue   │   │
│  │           │                                                             │   │
│  │           └──────────────────────────────────────────────────────────   │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  关键特性：                                                                      │
│  ─────────                                                                       │
│  1. 失败的计划存储在 plan_attempts（本地变量）                                   │
│  2. Plan Loop 成功后，丢弃所有 plan_attempts                                     │
│  3. 只向 Milestone Loop 返回 ValidatedPlan                                      │
│  4. 避免错误计划污染 milestone_ctx                                               │
│                                                                                 │
│  输入：milestone_ctx (包含 Verify 失败的反思)                                    │
│  输出：ValidatedPlan (已通过 Validate)                                          │
│  副作用：无（plan_attempts 是临时的）                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Plan Loop vs Milestone Loop

| 维度 | Plan Loop | Milestone Loop |
|-----|-----------|---------------|
| **循环目标** | 生成**有效计划** | 完成**整个 Milestone** |
| **失败类型** | Validate 失败 | Verify 失败 |
| **失败处理** | 本地重试（plan_attempts） | Remediate → 累积反思 |
| **上下文污染** | ❌ 不污染（临时变量） | ✅ 累积（milestone_ctx） |
| **循环结束条件** | 生成有效计划 OR 预算耗尽 | Verify 通过 OR 预算耗尽 |
| **输出** | ValidatedPlan | MilestoneResult |

---

## 三、Envelope（执行边界）

由 Validate 阶段生成，传递给 Tool Loop 使用：

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  Envelope = WorkUnit 的执行边界（由 Validate 生成）                              │
│  ═══════════════════════════════════════════════════                            │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                         │   │
│  │  allowed_tools: [read_file, grep, write_file, apply_patch, run_tests]  │   │
│  │  ─────────────                                                          │   │
│  │  这个 WorkUnit 只能调用这些工具，越界 = Policy Deny                     │   │
│  │                                                                         │   │
│  │  required_evidence: [test_pass(suite=X), file_modified(path=Y)]        │   │
│  │  ─────────────────                                                      │   │
│  │  必须产出这些证据才算完成                                               │   │
│  │                                                                         │   │
│  │  budget:                                                                │   │
│  │  ───────                                                                │   │
│  │    max_tool_calls: 30                                                   │   │
│  │    max_tokens: 50000                                                    │   │
│  │    max_wall_time: 180s                                                  │   │
│  │    max_stagnant_iterations: 3                                           │   │
│  │                                                                         │   │
│  │  risk_level: IDEMPOTENT_WRITE  (从 allowed_tools 最高风险派生)         │   │
│  │  ──────────                                                             │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Python 数据结构

```python
@dataclass
class Envelope:
    """WorkUnit 的执行边界"""

    # 允许调用的工具列表
    allowed_tools: list[str]

    # 必须产出的证据
    required_evidence: list[EvidenceCondition]

    # 预算限制
    budget: EnvelopeBudget

    # 风险级别（从 allowed_tools 派生）
    risk_level: RiskLevel


@dataclass
class EnvelopeBudget:
    """Envelope 的预算限制"""
    max_tool_calls: int = 30
    max_tokens: int = 50000
    max_wall_time_seconds: int = 180
    max_stagnant_iterations: int = 3


class RiskLevel(Enum):
    """风险级别"""
    READ_ONLY = "read_only"           # 只读操作
    IDEMPOTENT_WRITE = "idempotent"   # 幂等写入
    DESTRUCTIVE = "destructive"       # 破坏性操作
```

---

## 四、DonePredicate（完成条件）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  DonePredicate = 三部分组成                                                      │
│  ══════════════════════════                                                      │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Part 1: Evidence Conditions（证据条件）                                 │   │
│  │ ────────────────────────────────────────                                │   │
│  │ 必须收集到的证据：                                                      │   │
│  │ • test_pass(suite=UserServiceTest)                                      │   │
│  │ • file_modified(path=src/UserService.java)                             │   │
│  │ • diff_applied(patch_id=...)                                           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Part 2: Invariant Conditions（不变量条件，防半成品）                    │   │
│  │ ───────────────────────────────────────────────────                     │   │
│  │ • workspace_clean（没有未 commit 的脏状态）                             │   │
│  │ • lint_pass（代码格式正确）                                             │   │
│  │ • compile_pass（能编译通过）                                            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Part 3: 停滞检测（由 Budget 隐式提供）                                  │   │
│  │ ─────────────────────────────────────                                   │   │
│  │ • 连续 K 次迭代没有新增 evidence                                        │   │
│  │ • 连续 K 次迭代失败测试数不下降                                         │   │
│  │ • 连续 K 次迭代 diff 不变化                                             │   │
│  │ → 判定停滞，step 失败                                                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Tool Loop 结束 = Evidence✓ + Invariant✓                                       │
│               OR Budget 耗尽 → Fail                                            │
│               OR 停滞检测 → Fail                                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Python 数据结构

```python
@dataclass
class DonePredicate:
    """完成条件"""

    # Part 1: 证据条件
    evidence_conditions: list[EvidenceCondition]

    # Part 2: 不变量条件
    invariant_conditions: list[InvariantCondition]

    def is_satisfied(self, evidence: list[Evidence]) -> bool:
        """检查是否满足完成条件"""
        # 检查所有证据条件
        for condition in self.evidence_conditions:
            if not condition.check(evidence):
                return False

        # 检查所有不变量条件
        for invariant in self.invariant_conditions:
            if not invariant.check():
                return False

        return True


@dataclass
class EvidenceCondition:
    """证据条件"""
    condition_type: str  # "test_pass" | "file_modified" | "diff_applied"
    params: dict


@dataclass
class InvariantCondition:
    """不变量条件"""
    condition_type: str  # "workspace_clean" | "lint_pass" | "compile_pass"
```

---

## 五、预定义 Skills（WorkUnit 模板）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  SkillRegistry: 预定义的 WorkUnit 模板                                          │
│  ══════════════════════════════════════                                          │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Skill: FixFailingTest                                                   │   │
│  │ ────────────────────────                                                │   │
│  │ description: "修复一个失败的测试"                                       │   │
│  │ allowed_tools: [read_file, grep, write_file, apply_patch, run_tests]   │   │
│  │ budget: {calls: 30, time: 180s, stagnant: 3}                           │   │
│  │ evidence: [test_pass(suite={input.suite})]                             │   │
│  │ invariants: [lint_pass]                                                 │   │
│  │ input_schema: {suite: string}                                           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Skill: ImplementFeature                                                 │   │
│  │ ────────────────────────                                                │   │
│  │ description: "实现一个新功能"                                           │   │
│  │ allowed_tools: [read_file, grep, write_file, apply_patch,              │   │
│  │                 run_tests, run_lint]                                    │   │
│  │ budget: {calls: 50, time: 300s, stagnant: 5}                           │   │
│  │ evidence: [test_pass(suite={input.suite}),                             │   │
│  │            file_modified(pattern={input.pattern})]                     │   │
│  │ invariants: [lint_pass, compile_pass]                                   │   │
│  │ input_schema: {suite: string, pattern: string}                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Skill: RefactorModule                                                   │   │
│  │ ────────────────────────                                                │   │
│  │ description: "重构一个模块"                                             │   │
│  │ allowed_tools: [read_file, grep, write_file, apply_patch,              │   │
│  │                 run_tests, run_lint]                                    │   │
│  │ budget: {calls: 40, time: 240s, stagnant: 4}                           │   │
│  │ evidence: [test_pass(suite=all)]                                       │   │
│  │ invariants: [lint_pass, compile_pass, no_regression]                    │   │
│  │ input_schema: {module_path: string}                                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 六、Remediate（反思）机制

### 完整的 Milestone Loop

之前的文档遗漏了 **Remediate** 步骤，完整流程应该是：

```
┌──────────────────────────────────────────────────────────────────┐
│ Milestone Loop（完整版）                                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐         │
│  │ Observe │──▶│  Plan   │──▶│ Validate │──▶│ Execute │──┐      │
│  └─────────┘   └────▲────┘   └──────────┘   └─────────┘  │      │
│                     │                                      │      │
│                     │  累积的上下文：                       │      │
│                     │  • 上次迭代的反思                     │      │
│                     │  • 工具错误（含用户中断）              │      │
│                     │  • 已收集的证据                       │      │
│                     │                                      │      │
│              ┌──────┴────────┐                             │      │
│              │   Remediate   │◀────┐                       │      │
│              │ (LLM 反思)     │     │                       │      │
│              └───────────────┘     │                       │      │
│                                    │                       │      │
│                              ┌─────┴─────┐                 │      │
│                              │  Verify   │◀────────────────┘      │
│                              └─────┬─────┘                        │
│                                    │                              │
│                                    ├─▶ PASS → skip（退出循环）    │
│                                    └─▶ FAIL → Remediate           │
│                                                                   │
│  while not budget.exceeded()                                      │
└──────────────────────────────────────────────────────────────────┘
```

### Remediate 的作用

| 方面 | 说明 |
|-----|------|
| **触发条件** | Verify 阶段失败 |
| **执行者** | LLM（不可信） |
| **输入** | failure_reasons + tool_errors（含 user_interrupted） |
| **输出** | Reflection（反思总结） |
| **后续动作** | 累积到 context，回到 Plan 重新规划 |

---

## 七、数据结构定义

### MilestoneContext（累积上下文）

```python
@dataclass
class MilestoneContext:
    """
    Milestone 的执行上下文
    每次循环都在累积更多信息
    """

    # 初始信息
    user_input: str
    milestone_description: str

    # 累积的反思（每次 Remediate 添加）
    reflections: list[str] = field(default_factory=list)

    # 累积的工具错误（包括 user_interrupted）
    tool_errors: list["ToolError"] = field(default_factory=list)

    # 累积的证据
    evidence_collected: list[str] = field(default_factory=list)

    # 已尝试的方案（避免重复尝试失败的方案）
    attempted_plans: list[str] = field(default_factory=list)

    def add_reflection(self, reflection: str) -> "MilestoneContext":
        """添加反思"""
        self.reflections.append(reflection)
        return self

    def add_error(self, error: "ToolError") -> "MilestoneContext":
        """添加错误"""
        self.tool_errors.append(error)
        return self
```

### ToolError（工具错误）

```python
@dataclass
class ToolError:
    """
    工具执行错误
    包括用户手动中断的情况
    """
    error_type: str  # "tool_failure" | "user_interrupted" | "timeout"
    tool_name: str
    message: str
    user_hint: str | None = None  # 用户中断时的提示词


class UserInterruptedError(Exception):
    """用户手动中断工具执行"""
    def __init__(self, message: str, user_message: str | None = None):
        super().__init__(message)
        self.user_message = user_message  # 用户提供的提示词
```

### Budget（预算控制）

```python
@dataclass
class Budget:
    """
    预算限制
    避免无限循环
    """
    max_attempts: int = 10           # 最多尝试次数
    max_time_seconds: int = 600      # 最长执行时间（10分钟）
    max_tool_calls: int = 100        # 最多工具调用次数

    # 当前使用量
    current_attempts: int = 0
    current_tool_calls: int = 0
    start_time: float = field(default_factory=time.time)

    def exceeded(self) -> bool:
        """是否超出预算"""
        if self.current_attempts >= self.max_attempts:
            return True
        if time.time() - self.start_time >= self.max_time_seconds:
            return True
        if self.current_tool_calls >= self.max_tool_calls:
            return True
        return False

    def record_attempt(self):
        """记录一次尝试"""
        self.current_attempts += 1

    def record_tool_call(self):
        """记录一次工具调用"""
        self.current_tool_calls += 1
```

---

## 八、更新后的 _milestone_loop 伪代码（两层循环）

```python
async def _milestone_loop(
    self,
    milestone: Milestone,
    ctx: RunContext[DepsT],
) -> MilestoneResult:
    """
    Milestone Loop：不断尝试直到成功或预算耗尽

    架构改进：引入 Plan Loop 作为内层循环
    ════════════════════════════════════════

    两层循环设计：
    1. 外层 Milestone Loop：负责 Execute → Verify → Remediate
       - 只累积 Verify 失败的反思
       - milestone_ctx 跨迭代持久化

    2. 内层 Plan Loop：负责 Observe → Plan → Validate
       - 只累积 Validate 失败的尝试（临时的）
       - plan_attempts 在 Plan Loop 结束后丢弃

    好处：
    - 避免错误计划污染 milestone_ctx
    - 减少 context window 浪费
    - 职责分离更清晰
    """

    # === 初始化 ===
    milestone_ctx = MilestoneContext(
        user_input=milestone.user_input,
        milestone_description=milestone.description,
    )
    milestone_budget = Budget(
        max_attempts=10,
        max_time_seconds=600,
        max_tool_calls=100,
    )

    # === Milestone Loop (外层)：while not milestone_budget.exceeded() ===
    while not milestone_budget.exceeded():
        milestone_budget.record_attempt()

        await self.event_log.append(MilestoneAttemptEvent(
            milestone_id=milestone.milestone_id,
            attempt=milestone_budget.current_attempts,
        ))

        # ┌─────────────────────────────────────────────────────────────┐
        # │ Plan Loop (内层)：生成有效计划                               │
        # └─────────────────────────────────────────────────────────────┘
        try:
            validated_plan = await self._plan_loop(
                milestone=milestone,
                milestone_ctx=milestone_ctx,  # 传入 Verify 失败的反思
                ctx=ctx,
            )
        except PlanGenerationFailedError as e:
            # Plan Loop 耗尽预算，无法生成有效计划
            await self.event_log.append(MilestoneFailedEvent(
                milestone_id=milestone.milestone_id,
                reason="plan_generation_failed",
                attempts=milestone_budget.current_attempts,
                error=str(e),
            ))
            return MilestoneResult(
                success=False,
                error=f"Failed to generate valid plan: {e}",
                reflections=milestone_ctx.reflections,
            )

        # === Execute ===
        execute_result = await self._execute_with_error_handling(
            validated_steps=validated_plan.steps,
            milestone_ctx=milestone_ctx,
            budget=milestone_budget,
            ctx=ctx,
        )

        # === Verify ===
        verify_result = await self._verify(milestone, execute_result, ctx)

        if verify_result.passed:
            # skip：达到 milestone 条件，退出循环
            await self.event_log.append(MilestoneCompletedEvent(
                milestone_id=milestone.milestone_id,
                attempts=budget.current_attempts,
            ))

            return MilestoneResult(
                success=True,
                evidence=execute_result.evidence,
                attempts=budget.current_attempts,
            )

        else:
            # === Remediate ===
            reflection = await self._remediate(
                verify_result=verify_result,
                tool_errors=milestone_ctx.tool_errors,  # 包括 user_interrupted
                ctx=ctx,
            )

            # context/prompt 的修改：累积反思
            milestone_ctx.add_reflection(reflection)

            await self.event_log.append(RemediateEvent(
                milestone_id=milestone.milestone_id,
                attempt=budget.current_attempts,
                failure_reason=verify_result.failure_reason,
                reflection=reflection,
            ))

            # 继续 while 循环，带着更多信息重新 Plan

    # 预算耗尽，循环结束
    await self.event_log.append(MilestoneFailedEvent(
        milestone_id=milestone.milestone_id,
        reason="budget_exceeded",
        attempts=budget.current_attempts,
    ))

    return MilestoneResult(
        success=False,
        error=f"Budget exceeded after {budget.current_attempts} attempts",
        reflections=milestone_ctx.reflections,
    )
```

---

## 八点五、_plan_loop 伪代码实现

```python
async def _plan_loop(
    self,
    milestone: Milestone,
    milestone_ctx: MilestoneContext,
    ctx: RunContext[DepsT],
) -> ValidatedPlan:
    """
    Plan Loop：生成一个有效的计划（通过 Validate）

    职责：
    ══════
    - 生成通过 Validate 的计划
    - 本地管理失败的计划尝试（plan_attempts）
    - 成功后丢弃所有 plan_attempts，只返回 ValidatedPlan

    输入：
    ──────
    - milestone: 当前里程碑
    - milestone_ctx: 包含 Verify 失败的反思（持久的）
    - ctx: 运行上下文

    输出：
    ──────
    - ValidatedPlan: 已通过 Validate 的计划

    异常：
    ──────
    - PlanGenerationFailedError: Plan Loop 耗尽预算仍无法生成有效计划
    """

    # === 初始化 Plan Loop 预算 ===
    plan_budget = Budget(
        max_attempts=5,          # Plan Loop 最多尝试 5 次
        max_time_seconds=120,    # 最长 2 分钟
        max_tool_calls=0,        # Plan 阶段不调用工具
    )

    # === plan_attempts: 临时变量，记录失败的计划 ===
    plan_attempts: list[dict] = []

    # === Plan Loop: while not plan_budget.exceeded() ===
    while not plan_budget.exceeded():
        plan_budget.record_attempt()

        await self.event_log.append(PlanAttemptEvent(
            milestone_id=milestone.milestone_id,
            plan_attempt=plan_budget.current_attempts,
        ))

        # ┌──────────────────────────────────────────────────────────┐
        # │ Observe: 装配上下文                                       │
        # └──────────────────────────────────────────────────────────┘
        # 包含两部分：
        # 1. milestone_ctx.reflections: Verify 失败的反思（持久的）
        # 2. plan_attempts: Validate 失败的尝试（临时的）
        context = await self.context_assembler.assemble(
            milestone=milestone,
            milestone_context=milestone_ctx,  # Verify 失败的反思
            plan_attempts=plan_attempts,      # Validate 失败的尝试（本地）
            ctx=ctx,
        )

        # ┌──────────────────────────────────────────────────────────┐
        # │ Plan: LLM 生成计划                                        │
        # └──────────────────────────────────────────────────────────┘
        proposed = await self.model_adapter.generate(
            messages=self._build_plan_prompt(
                context=context,
                milestone_ctx=milestone_ctx,
                plan_attempts=plan_attempts,  # 告诉 LLM 上次为什么失败
            ),
            tools=self.tool_runtime.list_tools(),
        )
        proposed_steps = self._parse_steps(proposed)

        # ┌──────────────────────────────────────────────────────────┐
        # │ Validate: 验证计划                                        │
        # └──────────────────────────────────────────────────────────┘
        validation_result = await self._validate_steps(proposed_steps, ctx)

        if validation_result.is_valid:
            # ✓ 验证成功！
            await self.event_log.append(PlanValidatedEvent(
                milestone_id=milestone.milestone_id,
                plan_attempts=plan_budget.current_attempts,
                steps_count=len(validation_result.validated_steps),
            ))

            # 丢弃 plan_attempts，只返回有效计划
            return ValidatedPlan(
                steps=validation_result.validated_steps,
                metadata={
                    "plan_attempts": plan_budget.current_attempts,
                    "discarded_attempts": len(plan_attempts),
                }
            )

        else:
            # ✗ 验证失败，记录到 plan_attempts（本地变量）
            plan_attempts.append({
                "attempt": plan_budget.current_attempts,
                "proposed_steps": proposed_steps,
                "validation_errors": validation_result.errors,
                "timestamp": time.time(),
            })

            await self.event_log.append(PlanValidationFailedEvent(
                milestone_id=milestone.milestone_id,
                attempt=plan_budget.current_attempts,
                errors=validation_result.errors,
            ))

            # 继续循环，下次 Observe 会看到这次失败

    # === Plan Loop 预算耗尽 ===
    await self.event_log.append(PlanGenerationFailedEvent(
        milestone_id=milestone.milestone_id,
        attempts=plan_budget.current_attempts,
        total_errors=sum(len(a["validation_errors"]) for a in plan_attempts),
    ))

    raise PlanGenerationFailedError(
        f"Failed to generate valid plan after {plan_budget.current_attempts} attempts. "
        f"Total validation errors: {len(plan_attempts)}"
    )
```

### Plan Loop 的关键设计

| 设计点 | 说明 |
|-------|------|
| **临时变量** | `plan_attempts` 是本地变量，Plan Loop 结束后丢弃 |
| **不污染外层** | 失败的计划不写入 `milestone_ctx` |
| **快速失败** | 独立的 `plan_budget`（5 次尝试，2 分钟） |
| **信息流动** | 读取 `milestone_ctx.reflections`（Verify 失败的反思），但不修改它 |
| **审计日志** | 所有 plan_attempts 都记录到 EventLog（审计用） |
| **清晰输出** | 只返回 `ValidatedPlan`，不返回失败信息 |

---

## 九、Execute 阶段：用户中断处理

```python
async def _execute_with_error_handling(
    self,
    validated_steps: list[ValidatedStep],
    milestone_ctx: MilestoneContext,
    budget: Budget,
    ctx: RunContext[DepsT],
) -> ExecuteResult:
    """
    Execute 阶段：执行步骤并处理错误

    关键：处理用户中断（user_interrupted）
    """
    execute_result = ExecuteResult(success=True, evidence=[])

    for step in validated_steps:
        try:
            if step.step_type == StepType.ATOMIC:
                result = await self.tool_runtime.invoke(
                    step.tool_name,
                    step.tool_input,
                    ctx,
                )
            else:  # ITERATIVE (WorkUnit)
                result = await self._tool_loop(step, ctx)

            budget.record_tool_call()

            # 收集证据
            if result.evidence_ref:
                execute_result.evidence.append(result.evidence_ref)
                milestone_ctx.evidence_collected.append(result.evidence_ref)

        except UserInterruptedError as e:
            # === 用户手动中断 ===
            error = ToolError(
                error_type="user_interrupted",
                tool_name=step.tool_name,
                message=str(e),
                user_hint=e.user_message,  # 用户提供的提示词
            )
            milestone_ctx.add_error(error)
            execute_result.success = False

            await self.event_log.append(UserInterruptedEvent(
                step_id=step.step_id,
                tool_name=step.tool_name,
                user_message=e.user_message,
            ))

            # 不直接失败，继续执行其他步骤
            # 让 Remediate 阶段分析用户的意图
            continue

        except ToolExecutionError as e:
            # 工具执行失败
            error = ToolError(
                error_type="tool_failure",
                tool_name=step.tool_name,
                message=str(e),
            )
            milestone_ctx.add_error(error)
            execute_result.success = False

        except TimeoutError as e:
            # 超时
            error = ToolError(
                error_type="timeout",
                tool_name=step.tool_name,
                message=str(e),
            )
            milestone_ctx.add_error(error)
            execute_result.success = False

    return execute_result
```

---

## 十、Remediate 阶段：分析失败原因

```python
async def _remediate(
    self,
    verify_result: VerifyResult,
    tool_errors: list[ToolError],
    ctx: RunContext,
) -> str:
    """
    Remediate 阶段：LLM 反思失败原因

    特别处理用户中断，提取用户意图
    """

    # 构建基础反思 prompt
    prompt = f"""
Milestone verification failed. Analyze what went wrong and suggest improvements.

## Failure Reason
{verify_result.failure_reason}

## Evidence Collected
{ctx.collected_evidence}

## Steps Executed
{[s.description for s in verify_result.steps]}
"""

    # === 特别处理用户中断 ===
    user_interruptions = [e for e in tool_errors if e.error_type == "user_interrupted"]
    if user_interruptions:
        prompt += """

## IMPORTANT: User Interrupted The Following Operations
"""
        for error in user_interruptions:
            prompt += f"""
- Tool: `{error.tool_name}`
- User message: "{error.user_hint or 'No message provided'}"
"""
        prompt += """

The user interrupted these operations. This is important feedback!
Consider:
1. Why did the user interrupt? What does this tell us about their intent?
2. Should we try a completely different approach that respects user's feedback?
3. Can we achieve the milestone without these interrupted tools?
4. Is the user trying to guide us toward a better solution?
"""

    # 其他工具错误
    other_errors = [e for e in tool_errors if e.error_type != "user_interrupted"]
    if other_errors:
        prompt += f"""

## Tool Execution Errors
"""
        for error in other_errors:
            prompt += f"- [{error.error_type}] {error.tool_name}: {error.message}\n"

    prompt += """

## Required Analysis
Please provide:
1. Root cause analysis - why did we fail?
2. What should be done differently in the next attempt?
3. Alternative approaches to consider
4. Any assumptions that should be reconsidered
"""

    response = await self.model_adapter.generate(
        messages=[
            {
                "role": "system",
                "content": "You are analyzing task failures to improve future attempts. Pay special attention to user interruptions - they contain valuable feedback about what the user wants.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    return response.content
```

---

## 十一、Validate → Tool Loop 的数据传递

### Envelope 和 DonePredicate 的来源

**Validate 阶段**生成 Envelope 和 DonePredicate，**传递给 Tool Loop** 使用：

```
┌──────────────────────────────────────────────────────────────────┐
│ Validate 阶段的职责                                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  输入：ProposedStep (LLM 提议的步骤，不可信)                       │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ Gate 1: 工具/技能存在性检查                               │    │
│  │ Gate 2: 策略检查（IPolicyEngine）                         │    │
│  │ Gate 3: 从 Registry 派生安全字段（不信任 LLM）             │    │
│  └──────────────────────────────────────────────────────────┘    │
│                     ↓                                            │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ Gate 4: 生成 Envelope + DonePredicate（仅 WorkUnit）      │    │
│  │                                                           │    │
│  │  Envelope = {                                             │    │
│  │    allowed_tools: [从 Skill 定义获取],                    │    │
│  │    budget: {从 Skill 定义获取},                           │    │
│  │    required_evidence: [从 Skill 定义获取],                │    │
│  │    risk_level: max(allowed_tools 的风险级别)              │    │
│  │  }                                                        │    │
│  │                                                           │    │
│  │  DonePredicate = {                                        │    │
│  │    evidence_conditions: [从 Skill 定义获取],              │    │
│  │    invariant_conditions: [从 Skill 定义获取],             │    │
│  │  }                                                        │    │
│  └──────────────────────────────────────────────────────────┘    │
│                     ↓                                            │
│  输出：ValidatedStep（携带 Envelope 和 DonePredicate）           │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
                                    │
                     Validate 生成   │   Tool Loop 使用
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│ Tool Loop                                                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  while not done_predicate.is_satisfied(evidence):                │
│                                                                   │
│      # 使用 Envelope.allowed_tools 限制可用工具                   │
│      action = llm.next_action(allowed=envelope.allowed_tools)    │
│                                                                   │
│      # 门禁检查                                                   │
│      if action.tool not in envelope.allowed_tools:               │
│          deny()                                                  │
│                                                                   │
│      result = tool_runtime.invoke(...)                           │
│      evidence.append(result)                                     │
│                                                                   │
│      # 使用 Envelope.budget 检查预算                              │
│      if budget_exceeded(envelope.budget):                        │
│          break                                                   │
│                                                                   │
│  # 使用 DonePredicate 判断完成                                    │
│  return done_predicate.is_satisfied(evidence)                    │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 十二、完整循环图（四层循环）

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          四层循环（完整版 v2）                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ SESSION LOOP（跨 Context Window）                                       ┃ ║
║  ┃   Session #0 → Session #1..N                                            ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                     │                                         ║
║                                     ▼                                         ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ MILESTONE LOOP（外层，while not milestone_budget.exceeded()）           ┃ ║
║  ┃                                                                         ┃ ║
║  ┃   ┌────────────────────────────────────┐                                ┃ ║
║  ┃   │ PLAN LOOP（内层）                  │                                ┃ ║
║  ┃   │                                    │                                ┃ ║
║  ┃   │  ┌──────────┐  ┌──────┐  ┌─────┐  │                                ┃ ║
║  ┃   │  │ Observe  │─▶│ Plan │─▶│Valid│──┼─▶ ✓ → ValidatedPlan            ┃ ║
║  ┃   │  └──────────┘  └──────┘  └──┬──┘  │                                ┃ ║
║  ┃   │       ▲                      │     │                                ┃ ║
║  ┃   │       │    plan_attempts     │     │                                ┃ ║
║  ┃   │       │    (临时变量)         └─▶ ✗ │                                ┃ ║
║  ┃   │       └──────────────────────────  │                                ┃ ║
║  ┃   │                                    │                                ┃ ║
║  ┃   └────────────────────────────────────┘                                ┃ ║
║  ┃                     │                                                   ┃ ║
║  ┃                     ▼                                                   ┃ ║
║  ┃              ┌───────────┐   ┌────────┐                                ┃ ║
║  ┃              │  Execute  │──▶│ Verify │                                ┃ ║
║  ┃              └───────────┘   └────┬───┘                                ┃ ║
║  ┃                                   │                                    ┃ ║
║  ┃                                   ├─▶ ✓ PASS → 退出循环                ┃ ║
║  ┃                                   │                                    ┃ ║
║  ┃                                   └─▶ ✗ FAIL                           ┃ ║
║  ┃                                          ▼                              ┃ ║
║  ┃                                   ┌──────────┐                         ┃ ║
║  ┃                                   │Remediate │                         ┃ ║
║  ┃                                   │• 分析失败 │                         ┃ ║
║  ┃                                   │• 用户中断 │                         ┃ ║
║  ┃                                   └────┬─────┘                         ┃ ║
║  ┃                                        │                               ┃ ║
║  ┃                          累积反思到 milestone_ctx                       ┃ ║
║  ┃                          (下次 Plan Loop 会读取)                        ┃ ║
║  ┃                                        │                               ┃ ║
║  ┃                                        └─────────────────────┐         ┃ ║
║  ┃                                                              │         ┃ ║
║  ┃   continue (回到 Milestone Loop 开始，重新进入 Plan Loop)     │         ┃ ║
║  ┃                                                              │         ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┛ ║
║                                     │                                         ║
║                          (仅 WorkUnit) ▼                                      ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ TOOL LOOP（WorkUnit 内部迭代）                                          ┃ ║
║  ┃                                                                         ┃ ║
║  ┃   边界：Envelope (allowed_tools, budget) ← 来自 Validate                ┃ ║
║  ┃   结束：DonePredicate 满足 OR Budget 耗尽 ← 来自 Validate               ┃ ║
║  ┃                                                                         ┃ ║
║  ┃      ┌────────┐   ┌───────┐   ┌───────┐   ┌────────┐                  ┃ ║
║  ┃      │ Gather │──▶│  Act  │──▶│ Check │──▶│ Update │──┐               ┃ ║
║  ┃      └────────┘   └───────┘   └───────┘   └────────┘  │               ┃ ║
║  ┃           ▲                                            │               ┃ ║
║  ┃           └────────────────────────────────────────────┘               ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 循环层级总结

| 循环 | 职责 | 失败类型 | 累积的上下文 | 预算 |
|-----|------|---------|-------------|------|
| **Session Loop** | 跨 Context Window | Task 失败 | EventLog + Memory | 无限（可断点续跑） |
| **Milestone Loop** | 完成一个里程碑 | Verify 失败 | milestone_ctx.reflections（持久） | milestone_budget (10次尝试) |
| **Plan Loop** | 生成有效计划 | Validate 失败 | plan_attempts（临时，循环后丢弃） | plan_budget (5次尝试) |
| **Tool Loop** | WorkUnit 内部迭代 | DonePredicate 未满足 | WorkUnit 内部状态 | envelope.budget |

### 关键设计：信息隔离

```
milestone_ctx.reflections (持久)
    ↓ 传递给
Plan Loop (读取 reflections)
    ↓ 生成
plan_attempts (临时)
    ↓ 成功后丢弃
只返回 ValidatedPlan
    ↓
Execute → Verify
    ↓ 失败
Remediate → 添加新的 reflection 到 milestone_ctx
    ↓
下次 Milestone Loop 迭代时，Plan Loop 读取更新后的 reflections
```

**好处**：
- ✅ Validate 失败的计划不污染 milestone_ctx
- ✅ 减少 context window 浪费
- ✅ 职责分离：Plan Loop 专注于生成有效计划，Milestone Loop 专注于执行和验证
- ✅ 可审计：所有 plan_attempts 记录在 EventLog，但不影响后续推理

```

---

## 十三、关键问答

### Q1: 什么时候进入 Tool Loop？

```
只有 WorkUnit Step 才进入 Tool Loop。
Atomic Step 直接调用一次 ToolRuntime。
```

### Q2: Tool Loop 什么时候结束？

```
三选一：
1. DonePredicate 满足（Evidence✓ + Invariant✓）→ 成功
2. Budget 耗尽 → 失败
3. 停滞检测 → 失败
```

### Q3: Execute 什么时候结束？

```
所有 ValidatedSteps 都达到 Done/Fail 状态。
```

### Q4: Validate 和 ToolRuntime Gate 的区别？

```
Validate = 制定契约（一次性，在 Milestone 开始时）
ToolRuntime Gate = 执行契约（每次调用都检查）
```

### Q5: allowed_tools 从哪来？

```
从 SkillRegistry 的 SkillDefinition。
每个 Skill 预定义了它能用哪些工具。
```

### Q6: Plan Loop 什么时候进入？什么时候结束？

```
进入：Milestone Loop 每次迭代开始时
结束：
  ✓ 生成有效计划（通过 Validate）→ 返回 ValidatedPlan
  ✗ Plan Loop 预算耗尽 → 抛出 PlanGenerationFailedError
```

### Q7: Plan Loop 失败的计划去哪了？

```
- 记录到 EventLog（审计用）
- 存储在 plan_attempts（本地变量）
- Plan Loop 成功后，plan_attempts 被丢弃
- 不写入 milestone_ctx（避免污染）
```

### Q8: Milestone Loop 和 Plan Loop 的反思有什么区别？

```
Milestone Loop (milestone_ctx.reflections):
  - 来源：Verify 失败 → Remediate 生成
  - 内容：为什么执行失败、用户中断意图分析
  - 生命周期：持久化，跨 Milestone 迭代累积
  - 用途：指导下次 Plan Loop 生成更好的计划

Plan Loop (plan_attempts):
  - 来源：Validate 失败
  - 内容：为什么计划被拒绝（工具不存在、策略拒绝等）
  - 生命周期：临时，Plan Loop 结束后丢弃
  - 用途：指导 Plan Loop 内部的重试
```

### Q9: 为什么要引入 Plan Loop？

```
问题：
- Validate 失败的计划累积在 milestone_ctx 中
- 污染后续推理，浪费 context window
- 职责不清晰：Plan 和 Execute 混在一起

解决：
- Plan Loop 专注于"生成有效计划"
- Milestone Loop 专注于"执行计划并验证"
- 失败的计划不向外传播
- 信息隔离，减少干扰
```

### Q10: Plan Loop 和 Milestone Loop 如何交互？

```
Milestone Loop → Plan Loop:
  - 传递 milestone_ctx.reflections（Verify 失败的反思）
  - Plan Loop 读取（只读，不修改）

Plan Loop → Milestone Loop:
  - 返回 ValidatedPlan（成功）
  - 或抛出 PlanGenerationFailedError（失败）
  - plan_attempts 被丢弃，不传递

Milestone Loop → Remediate → Milestone Loop:
  - Verify 失败后，Remediate 分析
  - 添加 reflection 到 milestone_ctx
  - 下次迭代时，Plan Loop 读取新的 reflections
```

---

## 十四、总结

### 关键设计改进

| 维度 | 之前的设计 | 改进后的设计 |
|-----|----------|-------------|
| **循环结构** | 三层循环 | **四层循环**（新增 Plan Loop） |
| **循环方式** | `for attempt in range(3)` | `while not budget.exceeded()` |
| **退出条件** | 成功 or 3次尝试 | 成功 or 预算耗尽（次数+时间+工具调用） |
| **Plan 失败处理** | ❌ 累积在 milestone_ctx | ✅ **Plan Loop 内部隔离，成功后丢弃** |
| **上下文污染** | ❌ 错误计划污染 milestone_ctx | ✅ **信息隔离，只传递 ValidatedPlan** |
| **用户中断** | ❌ 未处理 | ✅ 作为 ToolError 处理，提取 user_hint |
| **信息累积** | 简单的 lessons_learned | ✅ 完整的 MilestoneContext |
| **Remediate** | 简单分析 | ✅ 特别分析用户中断的意图 |

### 用户中断处理流程

```
用户手动打断工具执行
        ↓
捕获 UserInterruptedError
        ↓
记录 ToolError(type="user_interrupted", user_hint=...)
        ↓
继续执行其他步骤（不直接失败）
        ↓
Verify 阶段检查
        ↓
Remediate 阶段分析用户意图
        ↓
下次 Plan 考虑用户反馈
```

### Plan Loop 引入的架构改进

```
┌─────────────────────────────────────────────────────────────────┐
│ 架构改进：从三层循环到四层循环                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  之前（三层）：                                                   │
│  ──────────                                                      │
│  Session Loop → Milestone Loop → Tool Loop                       │
│                     ↑                                            │
│              Observe → Plan → Validate → Execute → Verify        │
│              (Plan 失败累积在 milestone_ctx)                      │
│                                                                  │
│  现在（四层）：                                                   │
│  ──────────                                                      │
│  Session Loop → Milestone Loop → Plan Loop → Tool Loop           │
│                     ↑              ↑                             │
│              Execute → Verify  Observe → Plan → Validate         │
│              (Plan 失败隔离在 plan_attempts)                      │
│                                                                  │
│  关键变化：                                                       │
│  ────────                                                        │
│  1. Plan Loop 成为 Milestone Loop 的内层循环                      │
│  2. Plan Loop 专注于生成有效计划                                  │
│  3. Milestone Loop 专注于执行计划并验证                           │
│  4. 信息流动：                                                    │
│     milestone_ctx (持久) → Plan Loop (读取) → plan_attempts (临时) │
│     → ValidatedPlan (清洁输出) → Execute → Verify → Remediate    │
│     → milestone_ctx (累积新的 reflection)                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 需要更新的文档

- ✅ 本补充文档已更新（引入 Plan Loop 设计）
- 🔜 需要合并到 `Architecture_Final_Review_v1.md`
- 🔜 需要更新 `Architecture_Final_Review_v1.1.md` 的循环图

---

*文档状态：补充说明 v4 - 引入 Plan Loop，实现四层循环架构*
