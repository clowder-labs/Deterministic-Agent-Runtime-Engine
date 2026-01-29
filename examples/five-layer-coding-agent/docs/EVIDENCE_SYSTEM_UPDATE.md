# Evidence-Based Planning System - 实现总结

## 🎯 核心改动

基于用户旅程文档的要求，将 Plan 从"执行步骤序列"改为"验收标准和证据槽位"。

---

## 📋 设计理念

### ❌ 旧设计（错误）

**Plan = 执行步骤**：
```python
ProposedPlan(
    steps=[
        ProposedStep(capability_id="read_file", params={"path": "sample.py"}),  # 工具调用
        ProposedStep(capability_id="search_code", params={"pattern": "TODO"})
    ]
)
```
**问题**：Execute Loop 根本不用这个 plan（纯 ReAct 模式）

### ✅ 新设计（正确）

**Plan = 验收标准 + 证据槽位**：
```python
ProposedPlan(
    plan_description="理解项目结构和功能",
    steps=[  # 注意：这里的 "steps" 实际上是 "evidence requirements"
        ProposedStep(
            step_id="evidence_1",
            capability_id="file_evidence",  # 证据类型，不是工具名
            params={"expected_files": "至少 2 个源文件"},
            description="证据：已读取并理解源文件"
        ),
        ProposedStep(
            step_id="evidence_2",
            capability_id="summary_evidence",
            params={"required_content": ["项目类型", "主要功能"]},
            description="证据：生成项目总结"
        )
    ]
)
```

**优点**：
- 对齐用户旅程：Plan = 右栏（战略契约），Execute = 左栏（战术清单）
- Execute Loop 自由发挥（ReAct），完成后填充证据
- 用户看到的是"要达到什么"，不是"怎么做"

---

## 🔄 两种执行模式

### Execute Mode（默认）

**直接 ReAct 执行**：
```bash
> 这是一个什么项目？
→ Agent 直接调用工具（read_file, search_code），返回答案
→ 无需生成 plan，无需批准
```

**适用场景**：
- 快速探索
- 简单查询
- 开发调试

### Plan Mode

**证据驱动的计划模式**：
```bash
> /mode plan
> 探索这个项目

→ 生成 Plan（验收标准）：
   Evidence Requirements:
   1. [ ] file_evidence: 至少读取 2 个源文件
   2. [ ] summary_evidence: 生成项目总结

> /approve

→ Execute Loop 执行（ReAct），完成后填充证据：
   Evidence Requirements:
   1. [✓] file_evidence: 已读取 2 个文件: sample.py, README.md
   2. [✗] summary_evidence: 未生成总结
```

**适用场景**：
- 演示给领导（展示规划能力）
- 重要变更（需要审批）
- 合规要求（需要证据追踪）

---

## 📊 证据类型定义

当前支持的证据类型：

### 1. `file_evidence`
**定义**：证明已读取文件
**params**：
- `expected_files`: 期望读取的文件描述
- `min_count`: 最少文件数量

**填充逻辑**：
从 event log 提取 `tool.result` 事件（capability_id = "read_file"）

**显示示例**：
```
✓ 证据：已读取并理解源文件
  Type: file_evidence
  Expected: 至少 2 个源文件
  Evidence: 已读取 2 个文件: sample.py, README.md
```

### 2. `search_evidence`
**定义**：证明已执行搜索
**params**：
- `search_target`: 搜索目标
- `min_results`: 最少结果数

**填充逻辑**：
从 event log 提取 `tool.result` 事件（capability_id = "search_code"）

**显示示例**：
```
✓ 证据：搜索结果摘要
  Type: search_evidence
  Expected: TODO 注释
  Evidence: 已搜索: TODO
```

### 3. `summary_evidence`
**定义**：证明生成了总结/分析
**params**：
- `required_content`: 总结应包含的内容

**填充逻辑**：
从 event log 检查 `model.response` 事件（内容长度 > 100 字符）

**显示示例**：
```
✓ 证据：生成项目总结
  Type: summary_evidence
  Evidence: 已生成总结
```

---

## 🛠️ 修改的文件

### 1. `planners/llm_planner.py`

**修改内容**：重写 system prompt

**关键变化**：
```python
# 从这个：
"""
You must output tool execution steps:
{
    "steps": [
        {"capability_id": "read_file", "params": {...}}  # 工具调用
    ]
}
"""

# 改成这个：
"""
You must output evidence requirements:
{
    "steps": [  # "steps" 实际上是 "evidence requirements"
        {
            "capability_id": "file_evidence",  # 证据类型
            "params": {"expected_files": "..."},
            "description": "证据：已读取文件"
        }
    ]
}

Evidence types: file_evidence, search_evidence, summary_evidence
"""
```

### 2. `evidence_tracker.py`

**修改内容**：根据证据类型提取实际证据

**返回格式**：
```python
{
    1: {"status": "✓", "content": "已读取 2 个文件: sample.py, README.md"},
    2: {"status": "✗", "content": "未生成总结"}
}
```

**提取逻辑**：
- `file_evidence` → 查找 `tool.result` (read_file)
- `search_evidence` → 查找 `tool.result` (search_code)
- `summary_evidence` → 查找 `model.response` (长度 > 100)

### 3. `cli_display.py`

**修改内容**：显示证据槽位和填充状态

**显示格式**：
```
Evidence Requirements (2):

1. ✓ 证据：已读取并理解源文件
   Type: file_evidence
   Expected: 至少 2 个源文件
   Evidence: 已读取 2 个文件: sample.py, README.md

2. [ ] 证据：生成项目总结
   Type: summary_evidence
   Expected: 项目类型、主要功能
```

### 4. `cli_commands.py`

**修改内容**：默认模式改为 Execute

```python
# 从这个：
mode: ExecutionMode = ExecutionMode.PLAN

# 改成这个：
mode: ExecutionMode = ExecutionMode.EXECUTE  # Default: Execute mode
```

### 5. `interactive_cli.py`

**修改内容**：
- 移除硬编码的 `mode=ExecutionMode.PLAN`
- 更新启动消息
- 保持所有命令处理逻辑不变

---

## 🧪 测试验证

### 单元测试

```bash
PYTHONPATH=../.. python test_command_system.py
```

**测试内容**：
- ✅ 命令解析（/mode, /approve, etc.）
- ✅ 会话状态管理（默认 Execute mode）
- ✅ 证据槽位显示（待填 vs 已填）
- ✅ 证据提取逻辑

### 集成测试

```bash
# 确定性模式（无需 API）
PYTHONPATH=../.. python interactive_cli.py

# 测试流程：
> /help                     # 查看帮助
> /status                   # 确认默认 Execute mode
> 这是一个什么项目？          # Execute mode：直接执行
> /mode plan                # 切换到 Plan mode
> 探索项目结构               # Plan mode：生成计划
> /approve                  # 批准并执行
> /quit                     # 退出
```

---

## 📖 使用示例

### 示例 1：Execute Mode（默认）

```bash
$ PYTHONPATH=../.. python interactive_cli.py

🤖 Five-Layer Coding Agent CLI
Mode: execute (use /mode to switch)

> 这是一个什么项目？

🚀 Agent Execution
💭 Agent: Executing (ReAct mode)...

[Agent 自己决定调用 read_file, search_code...]

📊 Execution Result
✓ Task completed successfully!

Output: 这是一个 Python 示例项目...
```

### 示例 2：Plan Mode

```bash
> /mode plan
✓ Switched to PLAN mode

> 探索这个项目的代码结构

💭 Agent: Generating plan...
✓ Generated plan with 3 steps

============================================================
PROPOSED EXECUTION PLAN
============================================================

Goal: 理解项目的代码组织和主要模块

Evidence Requirements (3):

1. [ ] 证据：已读取并理解源文件
   Type: file_evidence
   Expected: 多个源文件

2. [ ] 证据：找到的主要函数和类结构
   Type: search_evidence
   Expected: 函数和类定义

3. [ ] 证据：代码结构总结
   Type: summary_evidence
   Expected: 模块划分、主要组件

============================================================
Type /approve to execute, /reject to cancel

> /approve

💭 Agent: Executing plan...

[Execute Loop 运行 ReAct，调用工具...]

📊 Execution Result
============================================================
EXECUTION RESULTS - EVIDENCE COLLECTED
============================================================

Goal: 理解项目的代码组织和主要模块

Evidence Requirements (3):

1. ✓ 证据：已读取并理解源文件
   Type: file_evidence
   Expected: 多个源文件
   Evidence: 已读取 3 个文件: sample.py, sample_test.py, __init__.py

2. ✓ 证据：找到的主要函数和类结构
   Type: search_evidence
   Expected: 函数和类定义
   Evidence: 已搜索: ^def\s+\w+, ^class\s+\w+

3. ✗ 证据：代码结构总结
   Type: summary_evidence
   Expected: 模块划分、主要组件
   Evidence: 未生成总结

============================================================

✓ Task completed successfully!
```

---

## 🎯 符合用户旅程

### 对齐用户旅程文档

**右栏（Plan - 战略契约）**：
- ✅ 定义里程碑目标和验收标准
- ✅ 包含必须填写的证据槽位
- ✅ 只读/审批模式
- ✅ Execute Loop 完成后填充证据

**左栏（Execute - 战术清单）**：
- ✅ LLM 自主决定工具调用（ReAct）
- ✅ 实时变动，可插入新任务
- ✅ 不修改右栏的 Plan

### Validator 的正确职责

**不是**验证"计划能否完成任务"（那是 LLM 的智商问题）

**而是**验证"计划格式是否合规"：
- 开发任务必须包含 `file_evidence` 坑位 ✅
- 探索任务必须包含 `summary_evidence` 坑位 ✅
- 缺少必需证据坑位？→ 驳回计划 ❌

---

## 🚀 优势总结

1. **语义正确**：Plan 是验收标准，不是执行步骤
2. **Execute Loop 自由**：ReAct 模式，LLM 自己决定工具调用
3. **证据可追溯**：每个验收标准都有对应证据
4. **用户友好**：用户看到的是"要达到什么"，不是"怎么做"
5. **符合设计**：完全对齐用户旅程文档

---

## 📝 未来扩展

### 更多证据类型

可以添加更多证据类型（对齐完整用户旅程）：
- `code_merge`: MR Link
- `quality_gate`: CI Job ID
- `validation`: Test URL
- `deployment`: Deployment URL

### Validator 增强

可以添加格式合规性检查：
- 开发任务必须有 `code_merge` 证据
- 测试任务必须有 `validation` 证据
- 部署任务必须有 `deployment` 证据

---

## ✅ 实现完成！

所有改动已完成并测试通过：
- ✅ LLMPlanner 生成证据要求（不是工具调用）
- ✅ Evidence Tracker 提取实际证据
- ✅ CLI Display 显示证据槽位
- ✅ 默认 Execute Mode
- ✅ /mode 切换支持
- ✅ 所有测试通过

可以直接运行演示：
```bash
PYTHONPATH=../.. python interactive_cli.py --openrouter
```
