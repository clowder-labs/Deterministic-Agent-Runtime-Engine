# 架构终稿评审 v1 - 补充说明

> 补充两个遗漏的关键设计点

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
│                                    ├─▶ PASS → 完成                │
│                                    └─▶ FAIL → Remediate           │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Remediate 的作用

| 方面 | 说明 |
|-----|------|
| **触发条件** | Verify 阶段失败 |
| **执行者** | LLM（不可信） |
| **输入** | VerifyResult.failure_reasons |
| **输出** | Reflection（反思总结） |
| **后续动作** | 回到 Plan 阶段，重新规划 |

### 更新后的 _milestone_loop 伪代码

```python
async def _milestone_loop(
    self,
    milestone: Milestone,
    ctx: RunContext[DepsT],
) -> MilestoneResult:
    """Milestone Loop：Observe → Plan → Validate → Execute → Verify → Remediate"""

    max_attempts = 3  # 最多重试 3 次

    for attempt in range(max_attempts):
        # === Observe ===
        context = await self.context_assembler.assemble(milestone, ctx)

        # === Plan (LLM, 不可信) ===
        proposed = await self.model_adapter.generate(
            messages=self._build_plan_prompt(context),
            tools=self.tool_runtime.list_tools(),
        )
        proposed_steps = self._parse_steps(proposed)

        # === Validate (系统, 可信) ===
        validated_steps = await self._validate_steps(proposed_steps, ctx)

        if not validated_steps:
            # 验证失败，无有效步骤
            continue  # 重新规划

        # === Execute ===
        execute_result = await self._execute(validated_steps, ctx)

        # === Verify ===
        verify_result = await self._verify(milestone, execute_result, ctx)

        if verify_result.passed:
            return MilestoneResult(
                success=True,
                evidence=execute_result.evidence,
            )
        else:
            # === Remediate（反思）===
            if attempt < max_attempts - 1:  # 还有重试机会
                reflection = await self._remediate(verify_result, ctx)

                # 将反思结果加入上下文，供下次 Plan 使用
                ctx.lessons_learned.append(reflection)

                await self.event_log.append(RemediateEvent(
                    milestone_id=milestone.milestone_id,
                    attempt=attempt,
                    failure_reason=verify_result.failure_reason,
                    reflection=reflection,
                ))

                # 回到 Plan（继续循环）
                continue
            else:
                # 已达最大重试次数
                return MilestoneResult(
                    success=False,
                    error=f"Milestone failed after {max_attempts} attempts",
                    failure_reason=verify_result.failure_reason,
                )

    return MilestoneResult(success=False, error="Max attempts exceeded")


async def _remediate(
    self,
    verify_result: VerifyResult,
    ctx: RunContext,
) -> str:
    """
    Remediate 阶段：LLM 反思失败原因

    Args:
        verify_result: 验证失败的结果
        ctx: 运行上下文

    Returns:
        反思总结（Reflection）
    """
    response = await self.model_adapter.generate(
        messages=[
            {
                "role": "system",
                "content": "Analyze why the milestone failed and provide insights for improvement.",
            },
            {
                "role": "user",
                "content": f"""
Milestone verification failed with the following reasons:
{verify_result.failure_reason}

Evidence collected:
{ctx.collected_evidence}

Steps executed:
{[s.description for s in verify_result.steps]}

Please analyze:
1. What went wrong?
2. What should be done differently in the next attempt?
3. Are there any assumptions that need to be reconsidered?
                """.strip(),
            },
        ],
    )

    return response.content
```

---

## 遗漏点 2：Validate → Tool Loop 的数据传递

### Envelope 和 DonePredicate 的来源

之前的文档没有明确说明 **Envelope** 和 **DonePredicate** 是在 **Validate 阶段生成**的。

```
┌──────────────────────────────────────────────────────────────────┐
│ Validate 阶段的职责                                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  输入：ProposedStep (LLM 提议的步骤，不可信)                       │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ Gate 1: 工具/技能存在性检查                               │    │
│  └──────────────────────────────────────────────────────────┘    │
│                     ↓                                            │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ Gate 2: 策略检查（IPolicyEngine）                         │    │
│  └──────────────────────────────────────────────────────────┘    │
│                     ↓                                            │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │ Gate 3: 从 Registry 派生安全字段                          │    │
│  │ • risk_level（从工具定义获取，不信任 LLM）                │    │
│  │ • timeout（从工具定义获取，不信任 LLM）                   │    │
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
│  输出：ValidatedStep                                              │
│  • 如果是 ATOMIC：直接执行                                        │
│  • 如果是 WORK_UNIT：                                             │
│    └─▶ 进入 Tool Loop                                            │
│        携带 Envelope 和 DonePredicate ─────────────┐              │
│                                                   │              │
└───────────────────────────────────────────────────┼──────────────┘
                                                    │
                                                    ▼
┌───────────────────────────────────────────────────┴──────────────┐
│ Tool Loop（使用 Envelope 和 DonePredicate）                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  while not done_predicate.is_satisfied(evidence):                │
│                                                                   │
│      # Gather → Act                                              │
│      action = llm.next_action(                                   │
│          allowed=envelope.allowed_tools  ◀── 使用 Envelope       │
│      )                                                            │
│                                                                   │
│      # Check（门禁）                                              │
│      if action.tool not in envelope.allowed_tools:  ◀── 检查边界  │
│          deny()                                                  │
│                                                                   │
│      # 执行工具                                                   │
│      result = tool_runtime.invoke(...)                           │
│                                                                   │
│      # Update                                                    │
│      evidence.append(result.evidence_ref)                        │
│                                                                   │
│      # 检查预算                                                   │
│      if budget_tracker.is_exceeded():  ◀── 使用 Envelope.budget  │
│          break                                                   │
│                                                                   │
│  # 循环结束条件                                                   │
│  return done_predicate.is_satisfied(evidence)  ◀── 使用 DonePredicate │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Validate → Tool Loop 的虚线连接

原始 mermaid 图中的虚线：

```mermaid
Validate -.->|"Envelope<br/>DonePredicate"| ToolLoop
```

**含义**：
- Validate 阶段**生成** Envelope 和 DonePredicate
- 这两个数据结构被**传递**给 Tool Loop
- Tool Loop 使用它们来：
  - 限制可用工具（Envelope.allowed_tools）
  - 控制预算（Envelope.budget）
  - 判断完成条件（DonePredicate）

### 代码实现

```python
async def _validate_steps(
    self,
    proposed: list[ProposedStep],
    ctx: RunContext,
) -> list[ValidatedStep]:
    """
    Validate 阶段：信任边界

    关键：
    1. 验证 LLM 提出的步骤
    2. 为 WorkUnit 生成 Envelope 和 DonePredicate ✅
    """
    validated = []

    for step in proposed:
        # Gate 1-3：省略...

        # Gate 4: 生成 Envelope 和 DonePredicate（仅 WorkUnit）
        if step.step_type == StepType.WORK_UNIT:
            # 从 SkillRegistry 获取 Skill 定义
            skill_def = self._get_skill_definition(step.skill_name)

            # 生成 Envelope
            safe_step.envelope = Envelope(
                allowed_tools=skill_def.allowed_tools,  # 从 Skill 定义
                budget=skill_def.budget,                # 从 Skill 定义
                required_evidence=skill_def.required_evidence,
                risk_level=self._derive_risk_level(skill_def.allowed_tools),
            )

            # 生成 DonePredicate
            safe_step.done_predicate = DonePredicate(
                evidence_conditions=skill_def.evidence_conditions,  # 从 Skill 定义
                invariant_conditions=skill_def.invariant_conditions,
                require_all=True,
            )

        validated.append(safe_step)

    return validated


# Tool Loop 接收并使用
async def _tool_loop(
    self,
    step: ValidatedStep,
    ctx: RunContext[DepsT],
) -> ToolLoopResult:
    """Tool Loop：使用 Validate 传递的 Envelope 和 DonePredicate"""

    # 从 ValidatedStep 获取
    envelope = step.envelope          # ✅ Validate 阶段生成
    done_pred = step.done_predicate   # ✅ Validate 阶段生成

    evidence = []
    budget = BudgetTracker(envelope.budget)

    while not done_pred.is_satisfied(evidence):  # ✅ 使用 DonePredicate
        # Gather → Act
        action = await self.model_adapter.generate(
            tools=[t for t in self.tool_runtime.list_tools()
                   if t.name in envelope.allowed_tools],  # ✅ 使用 Envelope
        )

        # Check
        if action.tool_name not in envelope.allowed_tools:  # ✅ 使用 Envelope
            continue

        # Execute
        result = await self.tool_runtime.invoke(...)

        # Update
        evidence.append(result.evidence_ref)
        budget.record_call()  # ✅ 使用 Envelope.budget

    return ToolLoopResult(success=done_pred.is_satisfied(evidence))
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
║  ┃ MILESTONE LOOP                                                          ┃ ║
║  ┃                                                                         ┃ ║
║  ┃   ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐              ┃ ║
║  ┃   │ Observe │──▶│  Plan   │──▶│ Validate │──▶│ Execute │──┐           ┃ ║
║  ┃   └─────────┘   └────▲────┘   └────┬─────┘   └─────────┘  │           ┃ ║
║  ┃                     │               │                      │           ┃ ║
║  ┃                     │               │ Envelope +           │           ┃ ║
║  ┃                     │               │ DonePredicate        │           ┃ ║
║  ┃                     │               │ (for WorkUnit)       │           ┃ ║
║  ┃                     │               ▼                      │           ┃ ║
║  ┃              ┌──────┴────────┐                             │           ┃ ║
║  ┃              │   Remediate   │◀────┐                       │           ┃ ║
║  ┃              │ (LLM 反思)     │     │                       │           ┃ ║
║  ┃              └───────────────┘     │                       │           ┃ ║
║  ┃                                    │                       │           ┃ ║
║  ┃                              ┌─────┴─────┐                 │           ┃ ║
║  ┃                              │  Verify   │◀────────────────┘           ┃ ║
║  ┃                              └─────┬─────┘                             ┃ ║
║  ┃                                    │                                   ┃ ║
║  ┃                                    ├─▶ PASS → 完成                     ┃ ║
║  ┃                                    └─▶ FAIL → Remediate                ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                     │                                         ║
║                          (仅 WorkUnit) ▼                                      ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ TOOL LOOP                                                               ┃ ║
║  ┃                                                                         ┃ ║
║  ┃   边界：Envelope (allowed_tools, budget)                                ┃ ║
║  ┃   结束：DonePredicate 满足 OR Budget 耗尽 OR 停滞                       ┃ ║
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

### 两个关键遗漏点

| 遗漏点 | 说明 | 影响 |
|-------|------|------|
| **Remediate** | Verify 失败后的 LLM 反思机制 | Milestone Loop 可以自我改进，而不是直接失败 |
| **Validate → Tool Loop 数据传递** | Envelope 和 DonePredicate 在 Validate 生成 | 明确了 WorkUnit 的执行边界来源 |

### 需要更新的文档

- ✅ 本补充文档已说明
- 🔜 需要更新 `Architecture_Final_Review_v1.md` 的循环图和伪代码
- 🔜 需要在接口文档中明确 Remediate 的接口定义

---

*文档状态：补充说明 - 待合并到主文档*
