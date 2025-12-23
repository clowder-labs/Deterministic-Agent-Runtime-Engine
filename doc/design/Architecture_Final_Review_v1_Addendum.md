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

## 十五、Session Loop 设计（跨对话持久化）

### 设计哲学

参考 Anthropic 的长运行 Agent 最佳实践，Session Loop 负责：

1. **上下文累积**：从上一轮对话的总结中读取关键信息
2. **Milestone 规划**：基于用户输入拆解成多个 Milestone
3. **顺序执行**：每个 Milestone 独立执行（无用户输入）
4. **上下文压缩**：总结整个 Session，为下一轮对话做准备

### Session Loop 伪代码

```python
async def _session_loop(
    self,
    user_input: str,  # 用户的本轮输入
    previous_session_summary: SessionSummary | None,  # 上一轮的总结
    ctx: RunContext[DepsT],
) -> SessionResult:
    """
    Session Loop：处理一轮用户交互

    设计原则：
    ════════════
    1. Milestone 是预先规划的（基于 user_input + previous_session_summary）
    2. Milestone 无用户输入（自主执行）
    3. Milestone 间通过 summary 传递上下文
    4. Session 结束后总结，压缩历史
    """

    # === 初始化 Session Context ===
    session_ctx = SessionContext(
        user_input=user_input,
        previous_session_summary=previous_session_summary,
        milestone_summaries=[],
        start_time=time.time(),
    )

    await self.event_log.append(SessionStartedEvent(
        user_input=user_input,
        has_previous_context=previous_session_summary is not None,
    ))

    # ┌─────────────────────────────────────────────────────────────┐
    # │ Plan Milestones: 拆解用户输入                                │
    # └─────────────────────────────────────────────────────────────┘
    milestones = await self._plan_milestones(
        user_input=user_input,
        previous_session_summary=previous_session_summary,
        ctx=ctx,
    )

    await self.event_log.append(MilestonesPlannedEvent(
        milestones=[m.description for m in milestones],
        total_count=len(milestones),
    ))

    # ┌─────────────────────────────────────────────────────────────┐
    # │ Execute Milestones: 顺序执行                                 │
    # └─────────────────────────────────────────────────────────────┘
    for i, milestone in enumerate(milestones):
        # 状态检查
        if self.state in [RuntimeState.STOPPED, RuntimeState.CANCELLED]:
            break

        # 从 checkpoint 恢复时，跳过已完成的
        if await self.checkpoint.is_completed(milestone.milestone_id):
            summary = await self.checkpoint.load_summary(milestone.milestone_id)
            session_ctx.milestone_summaries.append(summary)
            continue

        # ═══════════════════════════════════════════════════════
        # Milestone Loop: 执行单个 Milestone
        # ═══════════════════════════════════════════════════════
        milestone_result = await self._milestone_loop(
            milestone=milestone,
            previous_milestone_summaries=session_ctx.milestone_summaries,
            ctx=ctx,
        )

        # ═══════════════════════════════════════════════════════
        # Summarize: 总结当前 Milestone
        # ═══════════════════════════════════════════════════════
        summary = await self._summarize_milestone(
            milestone=milestone,
            result=milestone_result,
            milestone_index=i,
            total_milestones=len(milestones),
            ctx=ctx,
        )

        # 累积到 Session Context
        session_ctx.milestone_summaries.append(summary)

        # 持久化
        await self.event_log.append(MilestoneCompletedEvent(
            milestone_id=milestone.milestone_id,
            summary=summary,
        ))
        await self.checkpoint.save_milestone(milestone.milestone_id, summary)

    # ┌─────────────────────────────────────────────────────────────┐
    # │ Summarize Session: 压缩整个 Session                          │
    # └─────────────────────────────────────────────────────────────┘
    session_summary = await self._summarize_session(
        session_ctx=session_ctx,
        ctx=ctx,
    )

    await self.event_log.append(SessionCompletedEvent(
        summary=session_summary,
        duration_seconds=time.time() - session_ctx.start_time,
    ))

    await self.checkpoint.save_session(session_summary)

    return SessionResult(
        session_summary=session_summary,
    )
```

### 数据结构

```python
@dataclass
class SessionSummary:
    """
    Session 总结（压缩的上下文）

    传递给下一轮 Session，避免无限累积历史
    """
    session_id: str
    user_input: str

    # 执行结果（压缩）
    what_was_accomplished: str  # 1-2 句话
    key_deliverables: list[str]

    # 关键决策和经验
    important_decisions: list[str]
    lessons_learned: list[str]

    # 未完成的事项
    pending_tasks: list[str]

    # 统计
    milestone_count: int
    total_attempts: int
    duration_seconds: float


@dataclass
class MilestoneSummary:
    """
    单个 Milestone 的总结

    传递给下一个 Milestone（Session 内部）
    """
    milestone_id: str
    milestone_description: str

    # 产物
    deliverables: list[str]

    # 经验教训（简洁版）
    what_worked: str  # 1-2 句话
    what_failed: str  # 1-2 句话
    key_insight: str

    # 质量指标
    completeness: float  # 0.0 - 1.0
    termination_reason: str

    # 统计
    attempts: int
    duration_seconds: float


@dataclass
class SessionContext:
    """Session 级别的上下文"""
    user_input: str
    previous_session_summary: SessionSummary | None

    # 累积的 Milestone 总结（当前 Session 内部）
    milestone_summaries: list[MilestoneSummary] = field(default_factory=list)

    start_time: float = field(default_factory=time.time)
```

### 对话流程示例

```
用户第 1 轮输入："实现用户登录功能"
    ↓
Session Loop #1
    ↓ Plan Milestones
    [M1: 设计数据库表, M2: 实现认证逻辑, M3: 编写测试]
    ↓
    M1 → Milestone Loop → MilestoneResult → Summarize → MilestoneSummary #1
    M2 → Milestone Loop (读取 Summary #1) → MilestoneResult → Summarize → MilestoneSummary #2
    M3 → Milestone Loop (读取 Summary #1, #2) → MilestoneResult → Summarize → MilestoneSummary #3
    ↓
    Summarize Session → SessionSummary #1
    ↓
    保存到 Checkpoint

──────────────────────────────────────────────────────

用户第 2 轮输入："添加密码重置功能"
    ↓
Session Loop #2 (读取 SessionSummary #1)
    ↓ Plan Milestones (基于 user_input + SessionSummary #1)
    [M4: 生成重置令牌, M5: 发送邮件, M6: 更新密码]
    ↓
    M4 → Milestone Loop (读取 SessionSummary #1) → ...
    M5 → Milestone Loop (读取 SessionSummary #1 + MilestoneSummary #4) → ...
    M6 → ...
    ↓
    Summarize Session → SessionSummary #2
```

---

## 十六、Milestone 无"失败"概念

### 核心理解

**Milestone 是阶段性成果，不是测试用例**

- Agent 总是会产出东西，只是质量/完整度不同
- "成功/失败"由用户判断，不是 Agent 自己判断
- 即使写错了，也是一个产物，用户可以基于这个产物给出反馈

### 两个层次的区分

#### 1. Milestone Loop 内部（有质量检查）

```
while not milestone_budget.exceeded():
    Plan Loop → ValidatedPlan
    Execute Loop → ExecuteResult
    Verify → VerifyResult
        ├─ ✓ Verify PASS（内部判断）→ 达到预期，退出循环
        └─ ✗ Verify FAIL（内部判断）→ Remediate → 继续循环
```

#### 2. Milestone 整体（对外无"失败"）

```
MilestoneResult:
  - deliverables: [产出的文件、代码等]
  - completeness: 0.85  (完成度，0.0 - 1.0)
  - termination_reason: "verify_pass" | "budget_exceeded" | "stagnant"
  - quality_metrics: {tests_passing, tests_failing, ...}
```

无论 Milestone Loop 内部经历了多少次 Verify 失败，最终都会产出一个 **MilestoneResult**（包含产物、质量指标、完成度），不判断"成功/失败"。

### MilestoneResult 数据结构

```python
@dataclass
class MilestoneResult:
    """
    Milestone 执行结果（无"失败"概念）
    """
    milestone_id: str

    # 产物（无论质量如何，都有产物）
    deliverables: list[str]
    evidence: list[Evidence]

    # 质量评估
    quality_metrics: QualityMetrics
    completeness: float  # 0.0 - 1.0（Agent 自评）

    # 最后一次 Verify 的结果（供参考）
    last_verify_result: VerifyResult | None

    # 执行统计
    attempts: int
    tool_calls: int
    duration_seconds: float

    # 终止原因（不是"失败原因"）
    termination_reason: Literal[
        "verify_pass",           # Verify 通过，达到预期
        "budget_exceeded",       # 预算耗尽
        "stagnant",              # 停滞
        "plan_generation_failed" # 无法生成有效计划
    ]

    # 错误（如果有）
    errors: list[ToolError] = field(default_factory=list)
```

---

## 十七、Execute Loop 作为 LLM 驱动的执行循环

### 核心理解

**Plan 不是"完整的步骤列表"，而是"策略描述"**

```python
@dataclass
class ValidatedPlan:
    """Plan 是策略描述，不是步骤列表"""
    plan_description: str  # LLM 生成的计划文本

    # 例如：
    # "To implement login functionality:
    #  1. First, read the existing auth code
    #  2. Then, modify user.py to add login method
    #  3. Write tests to verify the logic
    #  4. Run tests to ensure everything works"
```

**Execute Loop 是 LLM 对话循环**

- LLM 看到：计划 + 当前进度 + 工具结果
- LLM 决定：下一步调用什么工具
- 执行工具 → 获得结果
- LLM 看到结果，决定：继续执行 / 调整策略 / 完成

### Execute Loop 伪代码

```python
async def _execute_plan(
    self,
    validated_plan: ValidatedPlan,
    milestone_ctx: MilestoneContext,
    budget: Budget,
    ctx: RunContext[DepsT],
) -> ExecuteResult:
    """
    Execute Loop: LLM 驱动的执行循环

    关键设计：
    ════════════
    1. LLM 决定下一步调用什么工具
    2. 区分 Execute Tool 和 Plan Tool
    3. Execute Tool → 进入 Tool Loop 确保执行成功
    4. Plan Tool (Skill) → 中止 Execute，回到 Milestone Loop 重新规划
    """

    execute_result = ExecuteResult(
        evidence=[],
        successful_tool_calls=[],  # 只记录成功的
        execution_trace=[],
    )

    execution_messages = [
        {
            "role": "system",
            "content": self._build_execution_system_prompt(milestone_ctx),
        },
        {
            "role": "user",
            "content": f"""
Execute this plan:

{validated_plan.plan_description}

Available tools: {self._format_tool_definitions()}

Execute step by step. After each tool call, assess and decide next action.
"""
        }
    ]

    max_iterations = 50

    for iteration in range(max_iterations):
        if budget.exceeded():
            execute_result.termination_reason = "budget_exceeded"
            break

        # ┌─────────────────────────────────────────────────┐
        # │ LLM 决定下一步                                   │
        # └─────────────────────────────────────────────────┘
        response = await self.model_adapter.generate(
            messages=execution_messages,
            tools=self.tool_runtime.list_tools(),
        )

        # LLM 没有工具调用 → 声明完成
        if not response.tool_calls:
            execute_result.termination_reason = "llm_declares_done"
            execute_result.llm_conclusion = response.content
            break

        # ┌─────────────────────────────────────────────────┐
        # │ 处理工具调用                                     │
        # └─────────────────────────────────────────────────┘
        tool_results = []

        for tool_call in response.tool_calls:
            tool = self.tool_runtime.get_tool(tool_call.name)

            if tool.is_plan_tool():  # Skill
                # ════════════════════════════════════════════
                # Plan Tool → 中止 Execute，回到 Milestone Loop
                # ════════════════════════════════════════════
                execute_result.encountered_plan_tool = True
                execute_result.plan_tool_name = tool_call.name
                execute_result.termination_reason = "plan_tool_encountered"
                return execute_result

            else:
                # ════════════════════════════════════════════
                # Execute Tool → 进入 Tool Loop
                # ════════════════════════════════════════════
                try:
                    result = await self._tool_loop_or_direct_invoke(
                        tool=tool,
                        tool_call=tool_call,
                        budget=budget,
                        ctx=ctx,
                    )

                    # 只记录成功的
                    execute_result.successful_tool_calls.append({
                        "tool": tool_call.name,
                        "input": tool_call.input,
                        "output": result.output,
                    })

                    if result.evidence_ref:
                        execute_result.evidence.append(result.evidence_ref)

                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": result.output,
                    })

                except (UserInterruptedError, ToolExecutionError) as e:
                    # 工具失败，反馈给 LLM
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": f"ERROR: {str(e)}",
                    })

        # 反馈给 LLM
        execution_messages.append({
            "role": "assistant",
            "content": response.content,
            "tool_calls": response.tool_calls,
        })
        execution_messages.extend(tool_results)

    if iteration >= max_iterations - 1:
        execute_result.termination_reason = "max_iterations_reached"

    return execute_result
```

### Execute Tool vs Plan Tool

| 维度 | Execute Tool | Plan Tool (Skill) |
|-----|-------------|-------------------|
| **目的** | 完成具体操作 | 复杂子任务，需要重新规划 |
| **例子** | bash, read_file, run_tests | FixFailingTest, ImplementFeature |
| **执行方式** | Tool Loop（确保目的达成） | 中止 Execute，回到 Milestone Loop |
| **返回** | 具体执行结果 | 触发重新规划 |

### ExecuteResult 数据结构

```python
@dataclass
class ExecuteResult:
    """Execute Loop 的结果"""
    evidence: list[Evidence]

    # 只记录成功的工具调用
    successful_tool_calls: list[dict]

    # 执行轨迹
    execution_trace: list[dict]

    # Plan Tool 遇到标记
    encountered_plan_tool: bool = False
    plan_tool_name: str | None = None

    # 终止原因
    termination_reason: Literal[
        "llm_declares_done",
        "plan_tool_encountered",
        "budget_exceeded",
        "max_iterations_reached",
    ] | None = None

    # LLM 的结论
    llm_conclusion: str | None = None
```

---

## 十八、Tool Loop 确保单步执行成功

### 核心理解

**Tool Loop 负责确保单个工具调用的目的达成**

```
Execute Loop 中某一步：
  LLM 决定：需要修改 auth.py 文件
    ↓
  进入 Tool Loop (针对这个 WorkUnit)
    ├─ Gather: 收集信息（读取文件）
    ├─ Act: 调用编辑工具
    ├─ Check: 检查是否修改成功（DonePredicate）
    ├─ Update: 更新状态
    └─ 如果 Check 失败 → 继续循环尝试

  Tool Loop 结束 → 返回结果（成功修改了文件）
    ↓
  Execute Loop 记录：edit_file → success
    ↓
  LLM 看到成功结果 → 决定下一步
```

### Tool Loop 伪代码

```python
async def _tool_loop(
    self,
    tool: ITool,
    tool_input: dict,
    envelope: Envelope,
    done_predicate: DonePredicate,
    budget: Budget,
    ctx: RunContext,
) -> ToolResult:
    """
    Tool Loop: 确保单个 WorkUnit 的目的达成

    例如：edit_file_workunit
    - Gather: 读取文件内容
    - Act: 调用编辑工具
    - Check: 验证文件是否修改成功
    - Update: 更新证据

    循环直到 DonePredicate 满足或 Budget 耗尽
    """

    tool_loop_ctx = ToolLoopContext(
        tool_name=tool.name,
        tool_input=tool_input,
        evidence=[],
    )

    tool_budget = envelope.budget

    while not tool_budget.exceeded():
        tool_budget.record_attempt()

        # Gather
        context = await self._gather_for_tool_loop(tool_loop_ctx, ctx)

        # Act
        action_result = await tool.execute(tool_input, context, ctx)
        tool_budget.record_tool_call()

        # Check
        if done_predicate.is_satisfied(action_result):
            # 目的达成
            return ToolResult(
                success=True,
                output=action_result.output,
                evidence_ref=action_result.evidence_ref,
            )

        # Update
        tool_loop_ctx.add_evidence(action_result.evidence_ref)

        # 检查停滞
        if self._is_tool_loop_stagnant(tool_loop_ctx):
            break

    # Tool Loop 失败（未达成目的）
    raise ToolExecutionError(
        f"Tool Loop for {tool.name} failed: DonePredicate not satisfied "
        f"after {tool_budget.current_attempts} attempts"
    )


async def _tool_loop_or_direct_invoke(
    self,
    tool: ITool,
    tool_call: ToolCall,
    budget: Budget,
    ctx: RunContext,
) -> ToolResult:
    """
    根据工具类型决定：
    - Atomic Tool → 直接调用
    - WorkUnit Tool → 进入 Tool Loop
    """

    if tool.is_atomic():
        # Atomic Tool: 直接调用一次
        result = await self.tool_runtime.invoke(
            tool_call.name,
            tool_call.input,
            ctx,
        )
        budget.record_tool_call()
        return result

    else:
        # WorkUnit Tool: 进入 Tool Loop
        envelope = tool.get_envelope()
        done_predicate = tool.get_done_predicate()

        result = await self._tool_loop(
            tool=tool,
            tool_input=tool_call.input,
            envelope=envelope,
            done_predicate=done_predicate,
            budget=budget,
            ctx=ctx,
        )

        return result
```

---

## 十九、更新后的完整循环图（五层循环）

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          五层循环（完整版 v3）                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ SESSION LOOP（跨对话，用户交互边界）                                     ┃ ║
║  ┃   User Input #1 → Session #1 → User Input #2 → Session #2 → ...         ┃ ║
║  ┃   每个 Session 开始前：读取 previous_session_summary                     ┃ ║
║  ┃   每个 Session 结束后：生成 session_summary（压缩上下文）                 ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                     │                                         ║
║                                     ▼                                         ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ MILESTONE LOOP（执行单个 Milestone，无用户输入）                         ┃ ║
║  ┃                                                                         ┃ ║
║  ┃   while not milestone_budget.exceeded():                                ┃ ║
║  ┃                                                                         ┃ ║
║  ┃   ┌────────────────────────────────────┐                                ┃ ║
║  ┃   │ PLAN LOOP（生成有效计划）           │                                ┃ ║
║  ┃   │  Observe → Plan → Validate         │                                ┃ ║
║  ┃   │  失败 → plan_attempts（临时）       │                                ┃ ║
║  ┃   │  成功 → ValidatedPlan（策略描述）   │                                ┃ ║
║  ┃   └────────────────────────────────────┘                                ┃ ║
║  ┃                     │                                                   ┃ ║
║  ┃                     ▼                                                   ┃ ║
║  ┃              ┌──────────────────┐                                       ┃ ║
║  ┃              │ EXECUTE LOOP     │                                       ┃ ║
║  ┃              │ (LLM 驱动执行)    │                                       ┃ ║
║  ┃              │                  │                                       ┃ ║
║  ┃              │ for each iter:   │                                       ┃ ║
║  ┃              │   LLM → tool_call│                                       ┃ ║
║  ┃              │   Execute Tool?  │──Yes──▶ Tool Loop ──▶ success        ┃ ║
║  ┃              │   Plan Tool?     │──Yes──▶ 中止，回到 Milestone Loop     ┃ ║
║  ┃              │   Done?          │──Yes──▶ ExecuteResult                ┃ ║
║  ┃              └──────────────────┘                                       ┃ ║
║  ┃                     │                                                   ┃ ║
║  ┃                     ▼                                                   ┃ ║
║  ┃              ┌──────────┐                                               ┃ ║
║  ┃              │  Verify  │                                               ┃ ║
║  ┃              └────┬─────┘                                               ┃ ║
║  ┃                   │                                                     ┃ ║
║  ┃                   ├─▶ ✓ PASS → MilestoneResult(completeness=1.0)       ┃ ║
║  ┃                   │                                                     ┃ ║
║  ┃                   └─▶ ✗ FAIL                                           ┃ ║
║  ┃                          ▼                                              ┃ ║
║  ┃                   ┌──────────┐                                         ┃ ║
║  ┃                   │Remediate │                                         ┃ ║
║  ┃                   └────┬─────┘                                         ┃ ║
║  ┃                        │                                               ┃ ║
║  ┃                        └──▶ continue（回到 while 开始）                 ┃ ║
║  ┃                                                                         ┃ ║
║  ┃   退出 Milestone Loop → MilestoneResult（无"失败"，只有完成度）          ┃ ║
║  ┃   → Summarize → MilestoneSummary（传给下一个 Milestone）                ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                     │                                         ║
║                          (WorkUnit Tool) ▼                                    ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ TOOL LOOP（确保单个工具调用的目的达成）                                  ┃ ║
║  ┃                                                                         ┃ ║
║  ┃   while not tool_budget.exceeded():                                     ┃ ║
║  ┃      Gather → Act → Check (DonePredicate) → Update                      ┃ ║
║  ┃      成功 → ToolResult                                                  ┃ ║
║  ┃      失败 → continue                                                    ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 循环层级总结（更新）

| 循环 | 职责 | 输入 | 输出 | 预算 |
|-----|------|------|------|------|
| **Session Loop** | 跨对话持久化 | user_input + previous_session_summary | SessionSummary | 无限（可断点续跑） |
| **Milestone Loop** | 完成一个里程碑 | previous_milestone_summaries | MilestoneResult（无"失败"） | milestone_budget (10次) |
| **Plan Loop** | 生成有效计划 | milestone_ctx.reflections | ValidatedPlan（策略描述） | plan_budget (5次) |
| **Execute Loop** | LLM 驱动执行 | ValidatedPlan | ExecuteResult（成功的工具调用） | 50 iterations |
| **Tool Loop** | 确保单步成功 | tool_input + Envelope | ToolResult | envelope.budget |

---

## 二十、关键设计总结

### 架构演进

| 版本 | 循环层级 | 关键改进 |
|-----|---------|---------|
| v1 | 3层（Session → Milestone → Tool） | 基础循环架构 |
| v2 | 4层（+ Plan Loop） | Plan Loop 隔离 Validate 失败的计划 |
| **v3** | **5层（+ Execute Loop）** | **Execute Loop 作为 LLM 驱动的执行循环** |

### v3 的关键设计点

1. **Session Loop**：跨对话持久化，上下文压缩
2. **Milestone 无"失败"**：只有完成度和产物状态
3. **Plan 是策略描述**：不是步骤列表
4. **Execute Loop 是 LLM 对话**：动态决策，遇到 Plan Tool 中止
5. **Tool Loop 确保单步成功**：只记录成功的工具调用
6. **Execute Tool vs Plan Tool**：区分具体操作和复杂子任务

### 信息流动

```
Session Summary (压缩)
    ↓
Milestone Loop (读取 previous summaries)
    ↓
Plan Loop (读取 reflections) → ValidatedPlan (策略)
    ↓
Execute Loop (LLM 驱动) → 成功的 tool_calls
    ↓
Verify (检查质量)
    ↓ 失败
Remediate (反思) → reflection
    ↓
下次 Milestone 迭代
    ↓
MilestoneResult (completeness + deliverables)
    ↓
MilestoneSummary (压缩)
    ↓
SessionSummary (再压缩)
```

---

*文档状态：补充说明 v5 - 引入 Session Loop 和 Execute Loop，实现五层循环架构*
