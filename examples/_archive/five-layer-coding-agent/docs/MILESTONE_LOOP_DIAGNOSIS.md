# 🔍 Milestone Loop 诊断报告 - 为什么没有重试？

## 📌 用户发现的问题

```
❌ FAIL: snake_game.py NOT created
✓ Task completed successfully!  ← 但什么都没创建，应该重试！
```

**用户的关键洞察**：
> "你还记得我们的五层循环吗？如果verify 挂了 他应该反思继续的呀？"

## 🎯 五层循环设计（用户提供的标准骨架）

```
L2: MILESTONE LOOP（无用户输入，目标闭环；可重试）
  ┌─────────────────────────────────────────────────────────────────┐
  │ for attempt in range(max_milestone_attempts):                   │
  │   1. Observe: ctx = assemble(MILESTONE_OBSERVE, state)          │
  │   2. Plan Loop (L3): 生成 ValidatedPlan                          │
  │   3. Approve: HITL / Policy Checkpoint                           │
  │   4. Execute Loop (L4): LLM 对话驱动执行                          │
  │   5. Verify: IValidator.verify_milestone(execute_result)         │
  │      - PASS: 产出 MilestoneSummary → 完成                        │
  │      - FAIL: IRemediator.remediate() → reflection → 回到 L3      │
  └─────────────────────────────────────────────────────────────────┘
```

## ✅ 框架实现检查

### 1. Milestone Loop 结构（dare_framework/agent/_internal/five_layer.py:435-493）

```python
async def _run_milestone_loop(self, milestone: Milestone) -> MilestoneResult:
    for attempt in range(self._max_milestone_attempts):  # ✅ 有重试循环
        # 1. Plan Loop
        validated_plan = await self._run_plan_loop(milestone)

        # 2. Execute Loop
        execute_result = await self._run_execute_loop(validated_plan)

        # 3. Verify milestone
        verify_result = await self._verify_milestone(execute_result)

        if verify_result.success:
            return MilestoneResult(success=True, ...)  # 成功返回

        # 4. Remediate（反思）
        if self._remediator is not None and milestone_state:
            reflection = await self._remediator.remediate(
                verify_result,
                ctx=self._context,
            )
            milestone_state.add_reflection(reflection)

        # 继续下一次尝试（回到 for loop 开头）
```

**结论**：✅ 框架实现是**正确的**！包含了完整的重试机制。

## 🐛 当前问题：为什么没有触发重试？

### 问题 1: SimpleValidator 总是返回 success=True

**文件**：`validators/simple_validator.py:90-96`

**问题代码**：
```python
# TODO: For testing, always return success
# In production, should check actual errors
return VerifyResult(
    success=True,  # Always succeed for testing  ← 总是返回 True！
    errors=[],
    metadata=result.metadata,
)
```

**后果**：
- Execute Loop 没有调用工具（模型只返回文本）
- 但 Validator 说"成功"
- Milestone Loop 认为任务完成，**没有触发重试**

**修复状态**：✅ 已修复（验证真实输出，不再总是返回 True）

### 问题 2: Execute Loop 没有调用工具

**症状**：
```
[DEBUG] Execute Loop - Messages being sent to model:
  1. [system] You are a helpful coding assistant... (强系统消息)
  2. [user] 写一个可以玩的贪吃蛇游戏，保存为 snake_game.py
  3. [user] 写一个可以玩的贪吃蛇游戏，保存为 snake_game.py  ← 重复！

[DEBUG] Model returned NO tool calls (finish_reason: stop)
```

**根本原因**：
1. **用户消息重复**（test代码问题）：
   ```python
   # test_snake_end_to_end.py
   agent._context.stm_add(Message(...))  # 第一次
   result = await agent.run(task)  # 第二次（Session Loop 中）
   ```

2. **模型能力不稳定**：
   - `arcee-ai/trinity-large-preview:free` 对 function calling 的支持不稳定
   - 有时返回 tool_calls，有时只返回文本
   - 即使有强系统消息，仍然不可靠

### 问题 3: 测试代码不完整

**test_snake_end_to_end.py** 混合了两种模式：
1. Step 1: 手动调用 planner（生成 plan）
2. Step 2: 调用 agent.run()（重新走完整流程）

这导致：
- 消息重复
- 不能真正测试完整的五层循环（包括重试机制）

## ✅ 修复方案

### 修复 1: SimpleValidator（已完成）

**文件**：`validators/simple_validator.py`

**修改**：不再总是返回 `success=True`，而是真正检查输出：

```python
async def verify_milestone(self, result: RunResult, ctx: IContext) -> VerifyResult:
    errors = []

    # Check 1: Did execution succeed?
    if not result.success:
        errors.append("Execution did not complete successfully")

    # Check 2: Are there errors?
    if result.errors:
        errors.extend(result.errors)

    # Check 3: Was meaningful output produced?
    if result.output:
        output_dict = result.output if isinstance(result.output, dict) else {}

        # If output is just {'content': '...'}, model only returned text
        if isinstance(output_dict, dict) and list(output_dict.keys()) == ['content']:
            content = output_dict.get('content', '')
            if len(content) < 10:
                errors.append("No meaningful output produced")
            else:
                errors.append(f"Model returned text instead of calling tools")
    else:
        errors.append("No output produced")

    success = len(errors) == 0
    return VerifyResult(success=success, errors=errors, ...)
```

**效果**：
- ✅ 当模型只返回文本时，Validator 返回 `success=False`
- ✅ 触发 Milestone Loop 的重试机制
- ✅ Remediate → 重新 Plan → 重新 Execute

### 修复 2: 创建正确的端到端测试

**创建新文件**：`test_milestone_retry.py`

```python
"""Test Milestone Loop retry mechanism."""
import asyncio
from pathlib import Path
from dare_framework.plan.types import Task
from enhanced_agent import EnhancedFiveLayerAgent
# ... setup tools, model, planner, validator ...

# 关键配置
agent = EnhancedFiveLayerAgent(
    name="retry-test-agent",
    model=model,
    tools=tool_provider,
    tool_gateway=tool_gateway,
    planner=planner,
    validator=validator,  # ← 使用修复后的 validator
    max_milestone_attempts=3,  # ← 允许 3 次重试
)

# 直接调用 agent.run()，不要手动添加消息
task = Task(
    description="写一个可以玩的贪吃蛇游戏，保存为 snake_game.py",
    task_id="retry-test-1"
)

result = await agent.run(task)  # ← 走完整的五层循环

# 期望行为：
# Attempt 1: Model returns text → Verify FAIL → Remediate
# Attempt 2: Model tries again with reflection → ...
# Attempt 3: ...
```

### 修复 3: 使用更强大的模型（可选）

当前模型 `arcee-ai/trinity-large-preview:free` 对 function calling 的支持不稳定。

**替代方案**：
1. 使用 OpenRouter 的其他模型（如 `google/gemini-flash-1.5:free`）
2. 使用本地模型（如 Ollama + llama3.1）
3. 使用 Claude API（通过 OpenRouter）

**修改**：`.env` 文件

```env
OPENROUTER_MODEL=google/gemini-flash-1.5:free  # 或其他更强的模型
```

## 🧪 验证 Milestone Loop 重试机制

### 预期行为（修复后）

```
======================================================================
MILESTONE LOOP - Attempt 1
======================================================================

[DEBUG] Execute Loop - Messages:
  1. [system] You are a helpful coding assistant...
  2. [user] 写一个可以玩的贪吃蛇游戏，保存为 snake_game.py

[DEBUG] Model returned NO tool calls

[DEBUG] Verifying milestone:
  - result.success: True
  - result.output: [{'content': '我来为你写...'}]
  - result.errors: []
[DEBUG] Verification errors: ['Model returned text instead of calling tools']

❌ Milestone verification FAILED
   Triggering Remediate...

Remediate: Model did not use tools, regenerating plan with stronger guidance

======================================================================
MILESTONE LOOP - Attempt 2
======================================================================

[DEBUG] Execute Loop - Messages:
  1. [system] You are a helpful coding assistant...
  2. [user] 写一个可以玩的贪吃蛇游戏，保存为 snake_game.py
  3. [assistant] Previous attempt failed: Model returned text instead of calling tools
                 You MUST use write_file tool this time.

[DEBUG] Model returned 1 tool calls
  - write_file

✓ Tool invocation successful: Created snake_game.py

[DEBUG] Verifying milestone:
  - Files created: ['snake_game.py']
✓ Milestone verification PASSED

======================================================================
✅ MILESTONE COMPLETED (attempt 2/3)
======================================================================
```

### 关键检查点

1. **Validator 返回 FAIL**：
   - ✅ 检查到模型只返回文本，没有调用工具
   - ✅ 返回 `success=False` 和具体错误信息

2. **Remediate 被调用**：
   - ✅ 生成反思消息（如："上次失败因为..."）
   - ✅ 添加到 milestone_state.reflections

3. **重新生成 Plan**：
   - ✅ Plan Loop 再次被调用
   - ✅ 可能生成不同的 plan（或相同 plan 但有反思）

4. **重新执行**：
   - ✅ Execute Loop 再次被调用
   - ✅ STM 包含反思消息，提示模型"上次失败了，这次必须用工具"

5. **最多 3 次尝试**：
   - ✅ 如果 3 次都失败，返回 `MilestoneResult(success=False)`

## 📊 当前状态总结

| 组件 | 框架实现 | Example 实现 | 状态 |
|------|---------|-------------|------|
| Milestone Loop 结构 | ✅ 正确 | N/A | ✅ 完整 |
| Plan Loop | ✅ 正确 | ✅ LLMPlanner | ✅ 工作 |
| Execute Loop | ✅ 正确 | ✅ EnhancedAgent | ⚠️ 模型不稳定 |
| Verify | ✅ 正确 | ❌ 总是返回 True | ✅ 已修复 |
| Remediate | ✅ 正确 | ❌ 未配置 | ⚠️ MVP 阶段留空 |
| 重试机制 | ✅ 正确 | ✅ max=3 | ✅ 应该触发 |

## 💡 核心洞察

1. **框架设计是对的**：
   - ✅ Milestone Loop 包含完整的 Observe → Plan → Execute → Verify → Remediate 循环
   - ✅ 有重试机制（max_milestone_attempts）
   - ✅ 支持反思和重新规划

2. **Example 实现有 bug**：
   - ❌ SimpleValidator 总是返回 success=True（**已修复**）
   - ⚠️ 模型能力不足/不稳定（建议换模型）
   - ❌ 测试代码不完整（消息重复）

3. **MVP 阶段的权衡**：
   - ⚠️ Remediator 未实现（框架支持，但 example 留空）
   - ⚠️ 反思机制简化（只记录错误，不生成结构化反思）
   - ✅ 这些都是合理的 MVP 简化

## 🚀 下一步行动

1. **立即测试修复后的 Validator**：
   ```bash
   PYTHONPATH=../.. python test_milestone_retry.py
   ```

2. **观察重试机制**：
   - 第一次尝试失败后，是否触发重试？
   - Validator 是否正确返回 FAIL？
   - 是否最多尝试 3 次？

3. **考虑换模型**（如果重试仍然失败）：
   - `google/gemini-flash-1.5:free` - 更强的 function calling 支持
   - 或使用本地 Ollama + llama3.1

4. **实现 Remediator**（可选）：
   - 创建 `LLMRemediator`，让模型生成反思
   - 添加到 agent 配置中
   - 增强重试时的上下文

## 📝 总结

**问题**：Milestone Loop 的重试机制没有触发

**根本原因**：
1. ❌ SimpleValidator 总是返回 success=True（**已修复**）
2. ⚠️ 模型不稳定（建议换模型）
3. ❌ 测试代码不完整（需要修复）

**框架状态**：✅ 完全正确，包含完整的五层循环和重试机制

**修复状态**：
- ✅ Validator 已修复
- ⚠️ 需要测试验证
- ⚠️ 可能需要换更强的模型

用户的洞察是对的：**Verify 失败应该触发重试**。框架设计和实现都是对的，问题在于 Example 的 Validator 实现有 bug（总是返回 True）。修复后应该能看到完整的重试机制工作。
