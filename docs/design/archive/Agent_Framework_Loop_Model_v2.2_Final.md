# Agent Framework 循环模型 v2.2 (Final)

> 综合 Anthropic Two-Part Solution + GPT 的精炼表述 + 完整数据结构

---

## 核心理念（一句话版）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  宏观 Validate = 制定契约（这件事允许做什么、需要什么证据、风险怎么控）          │
│  ToolRuntime Gate = 执行契约（每一步都检查你有没有作弊）                         │
│  Done Predicate = 结束条件（什么时候算完成）                                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 一、三层循环总览图

```
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                       ║
║                          AGENT FRAMEWORK 三层循环模型                                  ║
║                                                                                       ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ LAYER 1: SESSION LOOP （跨 Context Window）                                     ┃ ║
║  ┃                                                                                 ┃ ║
║  ┃   目的：长任务不断片，跨 session 保持状态                                       ┃ ║
║  ┃   产物：TaskPlan + ProgressLog + EventLog + Git                                ┃ ║
║  ┃                                                                                 ┃ ║
║  ┃   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐           ┃ ║
║  ┃   │  Session #0  │────────▶│  Session #1  │────────▶│  Session #N  │           ┃ ║
║  ┃   │ (Initializer)│         │  (Working)   │         │  (Working)   │           ┃ ║
║  ┃   └──────────────┘         └──────┬───────┘         └──────────────┘           ┃ ║
║  ┃                                   │                                             ┃ ║
║  ┃                                   ▼                                             ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                      │                                               ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ LAYER 2: MILESTONE LOOP （单个里程碑）                                          ┃ ║
║  ┃                                                                                 ┃ ║
║  ┃   目的：可控、可审计、可验收                                                    ┃ ║
║  ┃   核心：Plan → Validate → Execute → Verify                                     ┃ ║
║  ┃                                                                                 ┃ ║
║  ┃   ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐         ┃ ║
║  ┃   │ Observe │──▶│  Plan   │──▶│ Validate │──▶│ Execute │──▶│ Verify  │         ┃ ║
║  ┃   └─────────┘   └─────────┘   └────┬─────┘   └────┬────┘   └─────────┘         ┃ ║
║  ┃                                    │              │                             ┃ ║
║  ┃                              制定契约         执行契约                          ┃ ║
║  ┃                           (Envelope +      (Atomic 或                          ┃ ║
║  ┃                            DonePredicate)   WorkUnit)                          ┃ ║
║  ┃                                               │                                 ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                                  │                                   ║
║                                    ┌─────────────┴─────────────┐                     ║
║                                    │                           │                     ║
║                                    ▼                           ▼                     ║
║                           ┌───────────────┐           ┌───────────────┐              ║
║                           │  Atomic Step  │           │ WorkUnit Step │              ║
║                           │  (一次调用)   │           │ (多次迭代)    │              ║
║                           └───────────────┘           └───────┬───────┘              ║
║                                                               │                      ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┓ ║
║  ┃ LAYER 3: TOOL LOOP （WorkUnit 内部）                                            ┃ ║
║  ┃                                                                                 ┃ ║
║  ┃   目的：高效迭代，轻量门禁                                                      ┃ ║
║  ┃   边界：Envelope（allowed_tools + budget）                                     ┃ ║
║  ┃   结束：DonePredicate 满足 OR 预算耗尽 OR 停滞                                  ┃ ║
║  ┃                                                                                 ┃ ║
║  ┃      ┌────────┐   ┌───────┐   ┌───────┐   ┌────────┐                           ┃ ║
║  ┃      │ Gather │──▶│  Act  │──▶│ Check │──▶│ Update │──┐                        ┃ ║
║  ┃      └────────┘   └───────┘   └───────┘   └────────┘  │                        ┃ ║
║  ┃           ▲           │                               │                        ┃ ║
║  ┃           │           │ ToolRuntime Gate              │                        ┃ ║
║  ┃           │           │ (检查 allowed_tools)          │                        ┃ ║
║  ┃           └───────────┴───────────────────────────────┘                        ┃ ║
║  ┃                                                                                 ┃ ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 二、核心概念定义

### 2.1 Step 类型

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  Step 分类                                                                       │
│  ═════════                                                                       │
│                                                                                 │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │ ATOMIC STEP                     │  │ WORKUNIT STEP                       │  │
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

### 2.2 Envelope（执行边界）

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

### 2.3 DonePredicate（完成条件）

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

---

## 三、Runtime 伪代码（GPT版，精炼）

```python
def milestone_loop(milestone):
    # Observe
    context = assemble_context(milestone)
    
    # Plan (LLM, 不可信)
    plan = llm.propose_steps(context)  
    
    # Validate (系统, 可信)
    validated = system.validate(plan)  # → ValidatedSteps + Envelopes
    
    # Execute
    for step in validated.steps:
        if step.type == ATOMIC:
            # 直接调用，不需要 Tool Loop
            result = tool_runtime.invoke(step.tool, step.input)
            step.done = result.success
        
        else:  # WORK_UNIT
            # 进入 Tool Loop
            envelope = step.envelope
            done_pred = step.done_predicate
            
            while not done_pred.satisfied():
                # 检查预算/停滞
                if budget_exceeded(envelope) or stagnant():
                    step.fail("budget_or_stagnant")
                    break
                
                # Gather + Act
                action = llm.next_action(allowed=envelope.allowed_tools)
                
                # ToolRuntime Gate (检查 allowed_tools)
                result = tool_runtime.invoke(
                    action.tool, 
                    action.input,
                    allowed=envelope.allowed_tools  # 越界 = deny
                )
                
                # Check + Update
                update_evidence(result)
                update_progress()
            
            step.done = done_pred.satisfied()
    
    # Verify (确定性验收)
    report = system.verify(milestone.verification_spec)
    
    if report.passed:
        return SUCCESS
    else:
        # Remediate
        reflection = llm.reflect(report.failure_reasons)  # 可选
        return REPLAN  # 回到 Plan
```

---

## 四、预定义 Skills（WorkUnit 模板）

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

## 五、关键问答

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

---

## 六、三层循环职责对比

```
┌────────────────┬──────────────────────┬─────────────────┬────────────────────────┐
│ 层级           │ 目的                 │ 结束条件        │ 产物                   │
├────────────────┼──────────────────────┼─────────────────┼────────────────────────┤
│ Session Loop   │ 跨 context 不断片    │ Context满/      │ TaskPlan + ProgressLog │
│                │                      │ Milestone完成   │ + EventLog + Git       │
├────────────────┼──────────────────────┼─────────────────┼────────────────────────┤
│ Milestone Loop │ 可控可审计可验收     │ Verify pass/    │ ValidatedSteps +       │
│                │                      │ fail            │ Evidence + Report      │
├────────────────┼──────────────────────┼─────────────────┼────────────────────────┤
│ Tool Loop      │ 高效迭代             │ DonePredicate/  │ ToolResults +          │
│                │                      │ Budget/Stagnant │ 局部证据               │
└────────────────┴──────────────────────┴─────────────────┴────────────────────────┘
```

---

## 七、与 Anthropic 的对比

```
┌────────────────┬─────────────────────────────┬─────────────────────────────────┐
│ 维度           │ Anthropic                   │ 我们                            │
├────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ Session Loop   │ ✅ Two-Part Solution        │ ✅ 借鉴，加了 EventLog          │
├────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ Milestone Loop │ gather→act→verify→repeat    │ Plan→Validate→Execute→Verify   │
├────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ Validate       │ ❌ 没有                     │ ✅ 4个Gate，全是代码            │
├────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ WorkUnit/Skill │ ✅ Skills 概念              │ ✅ 加了 Envelope + DonePredicate│
├────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ 结束条件       │ 隐式                        │ ✅ 显式 DonePredicate           │
├────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ 证据链         │ 只有 progress file          │ ✅ EventLog + Hash Chain        │
└────────────────┴─────────────────────────────┴─────────────────────────────────┘
```

---

## 八、一句话总结

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  Session Loop 保证"长跑不断片"                                                  │
│  Milestone Loop 保证"可控可审计"                                                │
│  Tool Loop 保证"高效不官僚"                                                     │
│                                                                                 │
│  Validate = 制定契约                                                            │
│  ToolRuntime Gate = 执行契约                                                    │
│  DonePredicate = 结束条件                                                       │
│                                                                                 │
│  三层循环 + 三个概念 = 既能长跑，又敢上线，还不拖沓                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```
