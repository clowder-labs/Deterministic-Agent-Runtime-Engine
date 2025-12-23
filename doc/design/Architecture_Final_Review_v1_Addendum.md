# 架构终稿评审 v1 - 补充说明

> 补充两个遗漏的关键设计点，并优化 Milestone Loop 的实现

---

## 遗漏点 1：Remediate（反思）机制

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

## 数据结构定义

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

## 更新后的 _milestone_loop 伪代码

```python
async def _milestone_loop(
    self,
    milestone: Milestone,
    ctx: RunContext[DepsT],
) -> MilestoneResult:
    """
    Milestone Loop：不断尝试直到成功或预算耗尽

    特点：
    1. 累积信息：每次循环都积累更多上下文（反思、错误、证据）
    2. 用户中断：处理 user_interrupted 错误，提取用户提示词
    3. 预算限制：避免无限循环
    """

    # === 初始化 ===
    milestone_ctx = MilestoneContext(
        user_input=milestone.user_input,
        milestone_description=milestone.description,
    )
    budget = Budget(
        max_attempts=10,
        max_time_seconds=600,
        max_tool_calls=100,
    )

    # === 主循环：while not budget.exceeded() ===
    while not budget.exceeded():
        budget.record_attempt()

        await self.event_log.append(MilestoneAttemptEvent(
            milestone_id=milestone.milestone_id,
            attempt=budget.current_attempts,
        ))

        # === Observe ===
        # 装配上下文（包含所有累积的信息）
        context = await self.context_assembler.assemble(
            milestone=milestone,
            milestone_context=milestone_ctx,  # 累积的反思、错误、证据
            ctx=ctx,
        )

        # === Plan ===
        # LLM 根据增强的 context 规划（包含上次迭代的反思）
        proposed = await self.model_adapter.generate(
            messages=self._build_plan_prompt(
                context=context,
                reflections=milestone_ctx.reflections,       # 上次迭代的反思
                tool_errors=milestone_ctx.tool_errors,       # 包括 user_interrupted
                attempted_plans=milestone_ctx.attempted_plans,  # 避免重复
            ),
            tools=self.tool_runtime.list_tools(),
        )
        proposed_steps = self._parse_steps(proposed)

        # 记录本次尝试的方案
        milestone_ctx.attempted_plans.append(proposed.content)

        # === Validate ===
        validated_steps = await self._validate_steps(proposed_steps, ctx)

        if not validated_steps:
            # 验证失败，记录并继续循环
            milestone_ctx.add_reflection("Validation failed: no valid steps generated")
            continue

        # === Execute ===
        execute_result = await self._execute_with_error_handling(
            validated_steps=validated_steps,
            milestone_ctx=milestone_ctx,
            budget=budget,
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

## Execute 阶段：用户中断处理

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

## Remediate 阶段：分析失败原因

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

## 遗漏点 2：Validate → Tool Loop 的数据传递

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

## 更新后的完整循环图

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          三层循环（完整版）                                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ SESSION LOOP                                                            ┃ ║
║  ┃   Session #0 → Session #1..N                                            ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                     │                                         ║
║                                     ▼                                         ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ MILESTONE LOOP  (while not budget.exceeded())                           ┃ ║
║  ┃                                                                         ┃ ║
║  ┃   ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐              ┃ ║
║  ┃   │ Observe │──▶│  Plan   │──▶│ Validate │──▶│ Execute │──┐           ┃ ║
║  ┃   └─────────┘   └────▲────┘   └────┬─────┘   └─────────┘  │           ┃ ║
║  ┃                     │               │                      │           ┃ ║
║  ┃      累积的上下文：  │               │ 生成 Envelope +      │           ┃ ║
║  ┃      • reflections  │               │ DonePredicate        │           ┃ ║
║  ┃      • tool_errors  │               │ (for WorkUnit)       │           ┃ ║
║  ┃      • evidence     │               ▼                      │           ┃ ║
║  ┃                     │                                      │           ┃ ║
║  ┃              ┌──────┴────────┐                             │           ┃ ║
║  ┃              │   Remediate   │◀────┐                       │           ┃ ║
║  ┃              │ • 分析失败原因  │     │                       │           ┃ ║
║  ┃              │ • 分析用户中断  │     │                       │           ┃ ║
║  ┃              └───────────────┘     │                       │           ┃ ║
║  ┃                                    │                       │           ┃ ║
║  ┃                              ┌─────┴─────┐                 │           ┃ ║
║  ┃                              │  Verify   │◀────────────────┘           ┃ ║
║  ┃                              └─────┬─────┘                             ┃ ║
║  ┃                                    │                                   ┃ ║
║  ┃                                    ├─▶ PASS → skip（退出循环）         ┃ ║
║  ┃                                    └─▶ FAIL → Remediate                ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                     │                                         ║
║                          (仅 WorkUnit) ▼                                      ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ TOOL LOOP                                                               ┃ ║
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

---

## 总结

### 关键设计改进

| 维度 | 之前的设计 | 改进后的设计 |
|-----|----------|-------------|
| **循环方式** | `for attempt in range(3)` | `while not budget.exceeded()` |
| **退出条件** | 成功 or 3次尝试 | 成功 or 预算耗尽（次数+时间+工具调用） |
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

### 需要更新的文档

- ✅ 本补充文档已更新
- 🔜 需要合并到 `Architecture_Final_Review_v1.md`

---

*文档状态：补充说明 v2 - 包含用户中断处理和预算控制*
