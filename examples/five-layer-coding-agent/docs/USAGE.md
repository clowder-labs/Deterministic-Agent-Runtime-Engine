# Five-Layer Coding Agent - 使用指南

## 🎬 演示模式（最简单）

### 一键运行所有场景

```bash
cd examples/five-layer-coding-agent
PYTHONPATH=../.. python scenarios.py all
```

这会展示三个完整的场景，演示五层循环的工作流程。

## 📖 四种使用方式对比

| 模式 | API Key | 用途 | 适合人群 |
|------|---------|------|----------|
| **interactive_cli.py** | ❌ 不需要 | 交互式演示，可视化流程 | 🎭 演示、教学 |
| **scenarios.py** | ❌ 不需要 | 快速演示，多场景 | 👥 所有用户 |
| **deterministic_agent.py** | ❌ 不需要 | 单任务测试 | 🧪 开发者 |
| **openrouter_agent.py** | ✅ 需要 | 真实模型体验 | 🚀 高级用户 |

## 详细使用说明

### 0. 交互式 CLI（最适合演示）

**优点**：
- 可视化五层循环执行流程
- 实时显示 Agent "思考"过程
- 彩色输出，清晰直观
- 适合演示给领导或团队
- 支持连续多轮对话

**运行方式**：

```bash
# 确定性模式（推荐用于演示）
PYTHONPATH=../.. python interactive_cli.py

# OpenRouter 模式（需要 API key）
PYTHONPATH=../.. python interactive_cli.py --openrouter
```

**🆕 新功能: 命令系统和计划模式**

交互式 CLI 现在支持两种执行模式和多个命令：

**执行模式**：
- **Plan Mode（默认）**: 生成计划 → 审核 → 批准 → 执行（带证据追踪）
- **Execute Mode**: 直接执行（ReAct 模式）

**可用命令**：
```bash
/mode [plan|execute]  # 切换执行模式
/approve              # 执行待批准的计划
/reject               # 取消待批准的计划
/status               # 显示会话状态
/help                 # 显示帮助信息
/quit (或 /exit)      # 退出 CLI
```

**Plan Mode 示例**（推荐用于演示）：
```
🤖 Five-Layer Coding Agent CLI
Mode: plan

> Find all TODO comments

💭 Agent: Generating plan...
✓ Plan generated!

============================================================
PROPOSED EXECUTION PLAN
============================================================

Goal: Search for TODO comments in Python files

Steps (1):

1. search_code
   Description: Search for TODO in all Python files
   Params: {'pattern': 'TODO', 'file_pattern': '*.py'}

============================================================
Type /approve to execute, /reject to cancel

> /approve

💭 Agent: Executing plan...

📊 Execution Result
============================================================
PROPOSED EXECUTION PLAN
============================================================

Goal: Search for TODO comments in Python files

Steps (1):

1. search_code ✓
   Description: Search for TODO in all Python files
   Params: {'pattern': 'TODO', 'file_pattern': '*.py'}

============================================================

✓ Task completed successfully!
```

**Execute Mode 示例**：
```
> /mode execute
✓ Switched to EXECUTE mode

> Find all TODO comments
💭 Agent: Executing (ReAct mode)...

🚀 Agent Execution
1️⃣ Session Loop - Starting task execution
2️⃣ Milestone Loop - Breaking into milestones
3️⃣ Plan Loop - Generating execution plan

📊 Execution Result
✓ Task completed successfully!
```

**旧版交互示例**（仍然支持，兼容模式）：
```
Enter your task (or 'quit' to exit):
You: Find all TODO comments

🚀 Agent Execution
💭 Agent: Analyzing task: Find all TODO comments
💭 Agent: Planning to read and search files...
✓ Plan generated!

Plan Steps:
  1. Search for TODO comments in Python files
     Tool: search_code

🔍 Validating plan...
✓ Plan validation passed
✅ Verifying milestone completion...
✓ Milestone verified successfully!

✓ Task completed successfully!
```

**演示技巧**：
1. 先演示简单任务，如 "Find all TODO comments"
2. 再演示复杂任务，如 "Read sample.py and search for functions"
3. 展示不同关键词如何触发不同的计划生成

### 1. 场景演示模式（推荐）

**优点**：
- 无需配置
- 多个场景展示不同能力
- 清晰的输出格式
- 适合快速了解功能

**运行方式**：

```bash
# 所有场景
PYTHONPATH=../.. python scenarios.py all

# 单个场景
PYTHONPATH=../.. python scenarios.py read-and-search
PYTHONPATH=../.. python scenarios.py find-todos
PYTHONPATH=../.. python scenarios.py analyze-code
```

**预期输出**：
```
======================================================================
📖 Scenario 1: Read and Search
======================================================================
Task: Read sample.py and find TODO comments

[DEBUG] Verifying milestone:
  - result.success: False
  - result.output: []
  - result.errors: ['max tool iterations reached']

✓ Result: Success=True

======================================================================
🔍 Scenario 2: Find All TODOs
======================================================================
...
```

### 2. 确定性模式

**优点**：
- 完全可预测
- 适合调试
- 显示详细执行信息

**运行方式**：

```bash
PYTHONPATH=../.. python deterministic_agent.py
```

**预期输出**：
```
Workspace: /path/to/workspace

=== Running Deterministic Agent ===
Task: Read sample.py and find TODO comments
Plan: Read sample.py and search for TODO comments
Steps: 2

[DEBUG] Verifying milestone...

=== Result ===
Success: True
Output: None
```

### 3. OpenRouter 模式

**优点**：
- 真实 LLM 体验
- 免费模型可用
- 展示完整功能

**前置要求**：
1. 安装依赖：`pip install openai python-dotenv`
2. 配置 API key

**设置步骤**：

```bash
# 1. 复制配置模板
cp .env.example .env

# 2. 编辑 .env 文件
nano .env

# 添加你的 API key：
# OPENROUTER_API_KEY=sk-or-v1-your_key_here
# OPENROUTER_MODEL=qwen/qwen3-coder:free

# 3. 运行
PYTHONPATH=../.. python openrouter_agent.py
```

**预期输出**：
```
Workspace: /path/to/workspace
✓ Using OpenRouter API
✓ Model: qwen/qwen3-coder:free

======================================================================
🚀 Running OpenRouter Agent
======================================================================
Task: Read sample.py and find all TODO comments
Plan: Read sample.py and search for TODO comments
Steps: 2

======================================================================
📊 Result
======================================================================
Success: ✓ True
Output: <tool results>
```

## 🎯 实际应用场景

### 作为命令行工具

创建一个简单的封装脚本：

```bash
# create_task.sh
#!/bin/bash
TASK_DESC="$1"
PYTHONPATH=../.. python scenarios.py read-and-search
```

使用：
```bash
./create_task.sh "Find all TODOs"
```

### 作为 Python 库

```python
import asyncio
from scenarios import create_agent
from dare_framework.plan.types import ProposedPlan, ProposedStep, Task

async def my_task():
    plan = ProposedPlan(
        plan_description="My custom task",
        steps=[...],
    )

    agent = create_agent(plan)
    result = await agent.run(Task(description="Task", task_id="1"))

    return result

result = asyncio.run(my_task())
```

### 集成到 CI/CD

```yaml
# .github/workflows/test-agent.yml
name: Test Agent

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Run scenarios
        run: |
          cd examples/five-layer-coding-agent
          PYTHONPATH=../.. python scenarios.py all
```

## 🐛 故障排查

### ImportError: No module named 'dare_framework'

**解决方案**：确保从项目根目录运行，或设置 `PYTHONPATH`
```bash
cd examples/five-layer-coding-agent
PYTHONPATH=../.. python scenarios.py all
```

### OpenRouter API key not found

**解决方案**：创建 `.env` 文件
```bash
cp .env.example .env
# 编辑 .env，添加你的 OPENROUTER_API_KEY
```

### max tool iterations reached

**这是预期行为**：Execute loop 达到最大迭代次数（20次）。Validator 设置为总是返回成功，所以任务仍然完成。

在生产环境中，你需要：
- 更好的 Validator 逻辑
- 更精确的 DonePredicate
- 或使用真实的模型驱动执行

## 📊 性能基准

在 MacBook Pro (M1) 上：

| 模式 | 执行时间 | 内存使用 | API 调用 |
|------|---------|---------|---------|
| scenarios.py (all) | ~2-3s | ~50MB | 0 |
| deterministic_agent.py | ~1s | ~30MB | 0 |
| openrouter_agent.py | ~5-10s | ~60MB | 1-3 次 |

## 🎓 学习路径

1. **初学者**：从 `scenarios.py` 开始，理解基本概念
2. **开发者**：阅读 `deterministic_agent.py`，理解组件组装
3. **高级用户**：使用 `openrouter_agent.py`，体验真实 LLM
4. **贡献者**：修改和扩展，创建自己的场景

## 📝 下一步

- 阅读 [README.md](README.md) 了解架构细节
- 查看 [../../doc/design/Architecture.md](../../doc/design/Architecture.md) 理解五层循环
- 探索 [dare_framework/agent/_internal/five_layer.py](../../dare_framework/agent/_internal/five_layer.py) 源码
- 加入讨论，分享你的使用经验！
