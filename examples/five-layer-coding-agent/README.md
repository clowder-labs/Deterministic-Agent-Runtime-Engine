# Five-Layer Coding Agent Example

一个完整的五层循环 Coding Agent 示例，演示 DARE Framework 的核心架构 + Evidence-Based Planning 系统。

> **快速开始**: 直接运行 `python scenarios.py all` 查看所有演示场景！
>
> **交互式 CLI**: 运行 `PYTHONPATH=../.. python interactive_cli.py --openrouter` 体验完整的证据驱动规划流程
>
> **⚠️ 重要提示**: 免费模型对 function calling 的支持不稳定，建议使用付费模型或本地 Ollama。详见 [STATUS.md](STATUS.md)

## Architecture

The agent implements the full five-layer orchestration loop:

1. **Session Loop** - Top-level task lifecycle
2. **Milestone Loop** - Sub-goal tracking and verification
3. **Plan Loop** - Plan generation and validation
4. **Execute Loop** - Model-driven execution
5. **Tool Loop** - Individual tool invocations

```
┌─────────────────────────────────────────────────────────────────┐
│  Session Loop (跨 Context Window)                                │
│  └─ Milestone Loop (Observe → Plan → Approve → Execute → Verify) │
│     ├─ Plan Loop (生成有效计划，失败不外泄)                        │
│     ├─ Execute Loop (LLM 驱动执行)                               │
│     └─ Tool Loop (WorkUnit 内部闭环)                              │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Implementation Status

**详见 [STATUS.md](STATUS.md)** 查看完整的实现状态、已知问题和未来计划。

**核心更新**（2025-01-29）:
- ✅ 证据驱动规划系统（Evidence-Based Planning）
- ✅ 增强的 Execute Loop（添加系统消息指导模型使用工具）
- ✅ Milestone Loop 重试机制（验证失败 → 反思 → 重试）
- ⚠️ 免费模型不稳定（建议使用付费模型）

## Directory Structure

```
five-layer-coding-agent/
├── README.md                    # 主文档（你正在看的）
├── STATUS.md                    # 实现状态和已知问题
├── __init__.py
├── .env                         # 环境变量（不要提交！）
├── .env.example                 # 环境变量模板
│
├── Core Components (核心组件)
├── interactive_cli.py           # 交互式 CLI（推荐入口）
├── enhanced_agent.py            # 增强的 Agent（修复工具调用）
├── cli_commands.py              # 命令解析器
├── cli_display.py               # 显示格式化
├── evidence_tracker.py          # 证据提取逻辑
├── scenarios.py                 # 示例场景
├── deterministic_agent.py       # 确定性模式
├── openrouter_agent.py          # OpenRouter 模式
│
├── planners/                    # Planner 实现
│   ├── llm_planner.py          # LLM 证据规划器
│   ├── deterministic_planner.py
│   └── __init__.py
│
├── validators/                  # Validator 实现
│   ├── simple_validator.py     # 修复后的验证器
│   └── __init__.py
│
├── model_adapters/              # 模型适配器
│   ├── openrouter.py            # OpenRouter 适配器（支持工具调用）
│   └── __init__.py
│
├── tests/                       # 测试文件（已整理）
│   ├── test_milestone_retry.py # 测试重试机制
│   ├── test_tool_use.py        # 测试工具调用
│   └── ...
│
├── docs/                        # 文档（已整理）
│   ├── FIXES_SUMMARY.md        # Execute Loop 修复总结
│   ├── MILESTONE_LOOP_DIAGNOSIS.md
│   └── ...
│
└── workspace/                   # 测试工作区
    ├── sample.py
    └── sample_test.py
```

## Tools

The example uses built-in tools from `dare_framework.tool`:

- **ReadFileTool** - Read file contents (READ_ONLY risk level)
- **WriteFileTool** - Write file contents (IDEMPOTENT_WRITE risk level)
- **SearchCodeTool** - Search code patterns (READ_ONLY risk level)
- **RunCommandTool** - Execute commands (NON_IDEMPOTENT_EFFECT risk level)
- **EditLineTool** - Edit specific lines (IDEMPOTENT_WRITE risk level)

## 🚀 快速开始

### 方式 1: 运行演示场景（推荐）

最简单的方式，无需配置 API key：

```bash
# 从项目根目录
cd examples/five-layer-coding-agent

# 运行所有场景
PYTHONPATH=../.. python scenarios.py all

# 或运行单个场景
PYTHONPATH=../.. python scenarios.py read-and-search
PYTHONPATH=../.. python scenarios.py find-todos
PYTHONPATH=../.. python scenarios.py analyze-code
```

**输出示例**：
```
======================================================================
📖 Scenario 1: Read and Search
======================================================================
Task: Read sample.py and find TODO comments

✓ Result: Success=True
```

### 方式 2: 确定性模式（Deterministic Mode）

使用预定义计划，适合测试和 CI：

```bash
# 从项目根目录
PYTHONPATH=. python examples/five-layer-coding-agent/deterministic_agent.py
```

**特点**：
- ✅ 无需 API key
- ✅ 可预测的行为
- ✅ 适合自动化测试

**输出示例**：
```
=== Running Deterministic Agent ===
Task: Read sample.py and find TODO comments
Plan: Read sample.py and search for TODO comments
Steps: 2

[DEBUG] Verifying milestone...

=== Result ===
Success: True
```

### 方式 3: OpenRouter 模式（真实模型）

使用 OpenRouter API 和免费模型，体验真实的 LLM 驱动 Agent：

#### 1. Setup Environment

```bash
# Copy template
cp .env.example .env

# Edit .env and add your OpenRouter API key
nano .env
```

Your `.env` should look like:
```bash
OPENROUTER_API_KEY=sk-or-v1-your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=qwen/qwen3-coder:free
```

**⚠️ IMPORTANT SECURITY NOTE:**
- **NEVER commit your `.env` file** - it's already in `.gitignore`
- Only commit `.env.example` (the template)
- Keep your API keys secret

#### 2. Install Dependencies

```bash
pip install openai python-dotenv
```

#### 3. 运行 OpenRouter Agent

```bash
# 从项目根目录
cd examples/five-layer-coding-agent
PYTHONPATH=../.. python openrouter_agent.py
```

**输出示例**：
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

## Recommended Free Models

OpenRouter provides several free models for testing:

- `qwen/qwen3-coder:free` - Fast, good for coding tasks (recommended)
- `google/gemini-flash-1.5-8b-exp-0827:free` - Good quality
- `meta-llama/llama-3.2-3b-instruct:free` - Smaller model

Update `OPENROUTER_MODEL` in your `.env` file to try different models.

## 🎭 交互式演示（适合演示给领导看）

如果需要展示 Agent 的交互过程和工作流程，可以使用交互式 CLI：

```bash
# 确定性模式（无需 API key）
PYTHONPATH=../.. python interactive_cli.py

# 或使用真实模型
PYTHONPATH=../.. python interactive_cli.py --openrouter
```

**演示效果**：
```
🤖 Five-Layer Coding Agent - Interactive Demo
======================================================================

Enter your task (or 'quit' to exit):
You: Find all TODO comments

🚀 Agent Execution
======================================================================
1️⃣ Session Loop - Starting task execution
2️⃣ Milestone Loop - Breaking into milestones
3️⃣ Plan Loop - Generating execution plan

💭 Agent: Analyzing task: Find all TODO comments
💭 Agent: Planning to read and search files...
✓ Plan generated!

Plan Steps:
  1. Search for TODO comments in Python files
     Tool: search_code
     Params: {'pattern': 'TODO', 'file_pattern': '*.py'}

🔍 Validating plan...
✓ Plan validation passed
✅ Verifying milestone completion...
✓ Milestone verified successfully!

📊 Execution Result
======================================================================
✓ Task completed successfully!
```

**特点**：
- ✅ **可视化执行流程** - 清晰展示五层循环的每一层
- ✅ **实时反馈** - 显示 Agent 的"思考"过程
- ✅ **彩色输出** - 使用 ANSI 颜色码，更直观
- ✅ **交互式输入** - 可以连续输入多个任务
- ✅ **适合演示** - 非常适合给领导或团队演示

**演示建议**：
1. 先运行一个简单任务："Find all TODO comments"
2. 再试一个稍复杂的："Read sample.py and search for functions"
3. 展示不同的工具组合和计划生成过程

## 📋 示例场景详解

### Scenario 1: Read and Search (读取和搜索)
**任务**：读取 `sample.py` 并搜索 TODO 注释

**使用的工具**：
- `read_file` - 读取文件内容
- `search_code` - 搜索代码模式

**执行流程**：
1. Session Loop 初始化任务
2. Milestone Loop 分解为单个里程碑
3. Plan Loop 验证预定义计划
4. Execute Loop 按序执行两个工具
5. Tool Loop 执行每个工具调用

**运行**：
```bash
PYTHONPATH=../.. python scenarios.py read-and-search
```

### Scenario 2: Find TODOs (查找所有 TODO)
**任务**：在整个工作空间搜索 TODO 注释

**使用的工具**：
- `search_code` - 搜索所有 Python 文件

**特点**：
- 单步操作
- 演示简单的 Tool Loop
- 快速执行

**运行**：
```bash
PYTHONPATH=../.. python scenarios.py find-todos
```

### Scenario 3: Analyze Code (分析代码结构)
**任务**：读取文件并查找函数定义

**使用的工具**：
- `read_file` - 读取源码
- `search_code` - 使用正则搜索函数定义

**特点**：
- 演示正则表达式搜索
- 多步骤执行
- 结构化代码分析

**运行**：
```bash
PYTHONPATH=../.. python scenarios.py analyze-code
```

### 运行所有场景

```bash
PYTHONPATH=../.. python scenarios.py all
```

这会依次执行所有场景，展示完整的五层循环工作流程。

## Known Limitations

This is an example implementation with the following limitations:

- **Simple Validator** - Basic validation logic, not production-ready
- **No HITL Integration** - Human-in-the-loop is mocked
- **Limited Error Handling** - Basic error messages only
- **No Security Boundary** - `ISecurityBoundary` not fully implemented

See `openspec/changes/add-five-layer-example/design.md` for more details on design gaps.

## Troubleshooting

### "ModuleNotFoundError: No module named 'dare_framework'"

Run from project root with `PYTHONPATH=.`:
```bash
PYTHONPATH=. python examples/five-layer-coding-agent/deterministic_agent.py
```

### "OpenRouter API key is required"

Make sure you've created `.env` file with your API key:
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### "milestone failed after max attempts"

This usually means the validator couldn't verify the milestone. Check:
- Tool execution succeeded
- Plan steps are correct
- Validator logic matches your expectations

## Development

To modify this example:

1. Edit planners to change planning strategy
2. Edit validators to change verification logic
3. Add more tools to extend capabilities
4. Modify agents to change task scenarios

## 🎯 实际使用示例

### 作为库使用

你可以在自己的代码中使用这个 agent：

```python
from pathlib import Path
from dare_framework.agent import FiveLayerAgent
from dare_framework.plan.types import ProposedPlan, ProposedStep, Task
from dare_framework.tool import ReadFileTool, SearchCodeTool, NativeToolProvider, DefaultToolGateway
from examples.five_layer_coding_agent.planners import DeterministicPlanner
from examples.five_layer_coding_agent.validators import SimpleValidator

# 创建工具
tools = NativeToolProvider(tools=[ReadFileTool(), SearchCodeTool()])
gateway = DefaultToolGateway()
gateway.register_provider(tools)

# 创建计划
plan = ProposedPlan(
    plan_description="Your task description",
    steps=[
        ProposedStep(
            step_id="step1",
            capability_id="read_file",
            params={"path": "/path/to/file.py"},
        ),
    ],
)

# 创建 agent
agent = FiveLayerAgent(
    name="my-agent",
    model=your_model_adapter,  # 你的 ModelAdapter
    tools=tools,
    tool_gateway=gateway,
    planner=DeterministicPlanner(plan),
    validator=SimpleValidator(),
)

# 运行任务
result = await agent.run(Task(description="My task"))
print(f"Success: {result.success}")
```

### 自定义场景

复制 `scenarios.py` 并修改：

```python
# my_scenario.py
from scenarios import create_agent
from dare_framework.plan.types import ProposedPlan, ProposedStep, Task

async def my_custom_scenario():
    plan = ProposedPlan(
        plan_description="My custom task",
        steps=[
            # 添加你的步骤...
        ],
    )

    agent = create_agent(plan)
    task = Task(description="Custom task", task_id="custom-1")
    result = await agent.run(task)

    print(f"Result: {result.success}")

# 运行
import asyncio
asyncio.run(my_custom_scenario())
```

## 🔧 扩展和定制

### 添加新工具

1. 使用 framework 的工具：
```python
from dare_framework.tool import RunCommandTool, EditLineTool
tools_list = [ReadFileTool(), RunCommandTool(), EditLineTool()]
```

2. 或实现自己的工具（实现 `ITool` 接口）

### 自定义 Planner

实现 `IPlanner` 接口：

```python
class MyPlanner:
    @property
    def component_type(self):
        return ComponentType.PLANNER

    async def plan(self, ctx: IContext) -> ProposedPlan:
        # 你的计划生成逻辑
        return ProposedPlan(...)
```

### 自定义 Validator

实现 `IValidator` 接口：

```python
class MyValidator:
    @property
    def component_type(self):
        return ComponentType.VALIDATOR

    async def validate_plan(self, plan, ctx) -> ValidatedPlan:
        # 计划验证逻辑
        ...

    async def verify_milestone(self, result, ctx) -> VerifyResult:
        # 里程碑验证逻辑
        ...
```

## 📚 参考资料

- [DARE Framework 文档](../../doc/design/)
- [五层循环架构设计](../../doc/design/Architecture.md)
- [OpenSpec Proposal](../../openspec/changes/add-five-layer-example/)
- [OpenRouter API](https://openrouter.ai/)
- [FiveLayerAgent 源码](../../dare_framework/agent/_internal/five_layer.py)

## 🤝 贡献

发现问题或有改进建议？欢迎提 Issue 或 PR！
