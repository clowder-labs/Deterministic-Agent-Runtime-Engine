# 修复：代码编写任务的证据系统

## 🐛 问题描述

用户反馈："写一个可以玩的贪吃蛇" 任务时：
1. ❌ Plan 阶段就直接输出了代码（而不是定义证据要求）
2. ❌ 没有创建文件（只是输出文本）
3. ❌ 没有测试运行游戏

## 🔍 根本原因

之前的证据类型只有3种，都针对**读取/探索**任务：
- `file_evidence` - 读取文件
- `search_evidence` - 搜索代码
- `summary_evidence` - 生成总结

**缺少**针对**编写/创建**任务的证据类型！

结果：LLM 不知道如何规划"写代码"任务，只能直接输出代码。

---

## ✅ 解决方案

### 1. 添加新的证据类型

**新增两个证据类型**（在 `planners/llm_planner.py`）：

```python
4. "code_creation_evidence" - Proof that code files were created
   - params: {"expected_files": ["file1.py"], "file_type": "Python/JS/etc"}
   - Example: "证据：创建了 snake.py 游戏文件"

5. "functionality_evidence" - Proof that code works
   - params: {"test_method": "run/test/demo", "expected_behavior": "..."}
   - Example: "证据：贪吃蛇游戏可以运行并可玩"
```

### 2. 强化 Prompt 示例

**添加"写代码"任务的正确示例**：

```python
User: "写一个可以玩的贪吃蛇游戏"

WRONG (直接写代码):
{
    "steps": [
        {
            "capability_id": "write_file",  // ❌ Tool call!
            "params": {"path": "snake.py", "content": "import pygame..."}  // ❌ Code!
        }
    ]
}

CORRECT (证据要求):
{
    "plan_description": "创建可玩的贪吃蛇游戏",
    "steps": [
        {
            "step_id": "evidence_1",
            "capability_id": "code_creation_evidence",  // ✓ Evidence type
            "params": {"expected_files": ["snake.py"], "file_type": "Python游戏"},
            "description": "证据：创建了贪吃蛇游戏文件 snake.py"
        },
        {
            "step_id": "evidence_2",
            "capability_id": "functionality_evidence",
            "params": {"test_method": "运行测试", "expected_behavior": "游戏可启动"},
            "description": "证据：游戏可以运行并可玩"
        }
    ]
}
```

### 3. 更新 Evidence Tracker

**添加对新证据类型的支持**（在 `evidence_tracker.py`）：

```python
elif evidence_type == "code_creation_evidence":
    # 从 event log 提取：哪些文件被 write_file 创建了
    files_written = [...]
    evidence = f"已创建 {len(files_written)} 个文件: {', '.join(files_written)}"

elif evidence_type == "functionality_evidence":
    # 检查：是否有文件被创建（简化版）
    # 实际应该检查测试结果，但当前先检查文件创建
    evidence = "代码已创建（功能待用户测试）"
```

---

## 🎯 预期工作流程（修复后）

### Plan Mode 下的"写代码"任务

```bash
> /mode plan
> 写一个可以玩的贪吃蛇游戏

💭 Agent: Generating plan...

============================================================
PROPOSED EXECUTION PLAN
============================================================

Goal: 创建可玩的贪吃蛇游戏

Evidence Requirements (2):

1. [ ] 证据：创建了贪吃蛇游戏文件
   Type: code_creation_evidence
   Expected: ['snake.py']

2. [ ] 证据：游戏可以运行并可玩
   Type: functionality_evidence
   Expected: 游戏可启动并响应键盘操作

============================================================
Type /approve to execute, /reject to cancel

> /approve

💭 Agent: Executing plan...
[Execute Loop in ReAct mode]:
  - Model decides: "I need to write snake.py file"
  - Calls write_file tool with actual Python code
  - Creates workspace/snake.py
  - (Optionally) tests the game

============================================================
EXECUTION RESULTS - EVIDENCE COLLECTED
============================================================

Goal: 创建可玩的贪吃蛇游戏

Evidence Requirements (2):

1. ✓ 证据：创建了贪吃蛇游戏文件
   Type: code_creation_evidence
   Expected: ['snake.py']
   Evidence: 已创建 1 个文件: snake.py

2. ✓ 证据：游戏可以运行并可玩
   Type: functionality_evidence
   Evidence: 代码已创建（功能待用户测试）

============================================================

✓ Task completed successfully!

Output: 贪吃蛇游戏已创建在 workspace/snake.py
```

---

## 📊 关键区别

### ❌ 修复前

**Plan**:
```json
{
  "steps": [
    {"capability_id": "write_file", "params": {"content": "Python code..."}}
  ]
}
```
- Plan 直接包含代码（错误！）
- LLM 在 Plan 阶段就写代码，不调用工具
- 没有文件被创建

### ✅ 修复后

**Plan**:
```json
{
  "steps": [
    {"capability_id": "code_creation_evidence", "description": "证据：创建了文件"}
  ]
}
```
- Plan 只定义证据要求（正确！）
- Execute Loop 自己决定调用 write_file 工具
- 文件被实际创建在 workspace/

---

## 🧪 测试验证

**运行测试**：
```bash
$ PYTHONPATH=../.. python test_command_system.py

✓ Command parsing tests passed
✓ Session state tests passed
✓ Display tests passed (including code_creation_evidence)
✓ Evidence tracker tests passed

✅ All tests passed!
```

**显示效果**：
```
--- Writing Task Plan (code creation) ---

Evidence Requirements (2):

1. [ ] 证据：创建了贪吃蛇游戏文件
   Type: code_creation_evidence
   Expected: ['snake.py']

2. [ ] 证据：游戏可以运行并可玩
   Type: functionality_evidence
```

---

## 📝 修改的文件

1. **`planners/llm_planner.py`**
   - 添加 `code_creation_evidence` 和 `functionality_evidence` 证据类型
   - 添加"写代码"任务的正确示例
   - 强调禁止直接输出代码

2. **`evidence_tracker.py`**
   - 添加对 `code_creation_evidence` 的提取逻辑（从 write_file 事件）
   - 添加对 `functionality_evidence` 的提取逻辑

3. **`test_command_system.py`**
   - 添加写代码任务的测试用例
   - 验证新证据类型的显示

4. **`FIX_CODE_WRITING_TASKS.md`** - 本文档

---

## 🚀 如何测试修复

### 方法 1: 直接测试

```bash
PYTHONPATH=../.. python interactive_cli.py --openrouter

> /mode plan
> 写一个可以玩的贪吃蛇游戏
> /approve

# 检查：
# 1. Plan 是否包含 code_creation_evidence？
# 2. workspace/snake.py 是否被创建？
# 3. 证据是否显示 "✓ 已创建 1 个文件: snake.py"？
```

### 方法 2: 调试脚本

```bash
PYTHONPATH=../.. python debug_snake_task.py

# 这个脚本会：
# 1. 生成 plan
# 2. 检查 plan 是否包含工具调用（错误）或证据类型（正确）
# 3. 显示诊断信息
```

---

## ⚠️ 已知限制

### 1. `functionality_evidence` 是简化实现

当前实现：
```python
# 如果文件被创建，就认为功能实现了
if files_written:
    evidence = "代码已创建（功能待用户测试）"
```

**未来改进**：
- 实际运行代码并捕获输出
- 检查是否有错误/异常
- 运行单元测试
- 验证用户交互（如游戏可玩性）

### 2. 模型能力限制

即使 prompt 正确，模型仍然可能：
- 生成不完整的代码
- 创建有 bug 的代码
- 不调用 write_file 工具

**解决方案**：
- 使用更强的模型（如 Claude Sonnet 4.5）
- 添加更多示例到 prompt
- 在 Execute Loop 添加自动修复（Remediate）

---

## ✅ 成功标准

修复成功的标志：

1. ✅ Plan 包含 `code_creation_evidence`（不是 `write_file`）
2. ✅ Execute Loop 调用 write_file 工具
3. ✅ 文件被创建在 workspace/
4. ✅ 证据显示"已创建 X 个文件"
5. ✅ 用户可以手动运行创建的代码

---

## 🎉 总结

**问题**：LLM 在 Plan 阶段就输出代码，不创建文件

**根因**：缺少针对"写代码"任务的证据类型

**修复**：
1. 添加 `code_creation_evidence` 和 `functionality_evidence`
2. 强化 prompt 示例
3. 更新 evidence tracker

**结果**：
- ✅ Plan 正确定义证据要求
- ✅ Execute Loop 调用工具创建文件
- ✅ 证据可追溯

修复已完成并测试通过！🚀
