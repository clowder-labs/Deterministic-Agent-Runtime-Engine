# Example: Coding Agent

这是一个与 v2 Kernel 化架构对齐的 Coding Agent 示例，用于验证核心循环与组件装配。

## 目的

1. **验证框架设计** - 覆盖 Plan/Execute/Tool/Verify 闭环与证据落盘
2. **提供参考实现** - 展示 AgentBuilder 的组装方式
3. **可运行基线** - 提供一个确定性、可重复运行的示例入口

## 目录结构

```
coding-agent/
├── README.md           # 本文件
├── agent.py            # Agent 定义（入口）
├── openai_adapter.py   # OpenAI 适配器与计划生成器示例
├── plan_helpers.py     # 计划/证据闭环的辅助函数
├── tools/              # 示例工具
│   ├── __init__.py
│   ├── edit_line.py
│   ├── read_file.py
│   ├── write_file.py
│   ├── search_code.py
│   └── run_tests.py
└── skills/             # 示例技能（Plan Tool）
    ├── __init__.py
    └── fix_bug.py
```

## 运行方式

在示例目录内直接运行：

```bash
cd examples/coding-agent
PYTHONPATH=../.. python agent.py
```

或在项目根目录运行：

```bash
PYTHONPATH=. python examples/coding-agent/agent.py
```

## 核心对齐点

1. **闭环骨架（五层循环）**  
   v2 Kernel 固化骨架：Session/Milestone/Plan/Execute/Tool，示例以确定性 Planner 跑通接口闭环。

2. **Plan Tool 语义（占位）**  
   v2 里 Plan Tool 可作为“重规划信号”。示例当前以 `capability_id` 前缀 `plan:` 作为约定占位（接口在位）。

3. **可审计性**  
   示例可配置 EventLog 与 Checkpoint 路径，用于验证事件链与断点保存。

4. **确定性模式**  
   示例使用确定性 Planner，避免外部依赖（无网络、无真实模型调用）。

## 使用方式（代码侧）

在示例目录中运行时可直接导入：

```python
from agent import CodingAgent
from dare_framework.core.plan.planning import ProposedStep
from dare_framework.contracts.ids import generator_id

steps = [
    ProposedStep(step_id=generator_id("step"), capability_id="tool:read_file", params={"path": "README.md"})
]

agent = CodingAgent(
    workspace=".",
    plan_steps=steps,
)

result = await agent.run("读取 README.md 并解释内容")
print(result.success)
print(result.output)
```

## 使用 OpenAI 真实模型（v2 Planner）

`real_model_agent.py` 使用 `OpenAIPlanner` 生成 v2 `ProposedPlan`，再由 Kernel 执行工具闭环。

1) 设置环境变量：

```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选：代理或兼容网关
export OPENAI_DEBUG=1  # 可选：打印模型调用与计划解析摘要
```

如果使用 OpenRouter：

```bash
export OPENROUTER_API_KEY="your_openrouter_key"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export OPENROUTER_HTTP_REFERER="https://your.app"  # 可选
export OPENROUTER_APP_TITLE="dare-example"         # 可选
```

2) 代码示例（真实模型执行工具调用）：

```python
from dare_framework.builder import AgentBuilder
from dare_framework.core.event.local_event_log import LocalEventLog
from openai_adapter import OpenAIModelAdapter, OpenAIPlanner, tool_definitions_from_tools
from tools import ReadFileTool, WriteFileTool, SearchCodeTool, RunTestsTool

tools = [
    ReadFileTool(workspace="."),
    WriteFileTool(workspace="."),
    SearchCodeTool(workspace="."),
    RunTestsTool(),
]

adapter = OpenAIModelAdapter(model="gpt-4o-mini")
planner = OpenAIPlanner(
    model=adapter,
    tool_definitions=tool_definitions_from_tools(tools),
    plan_tools=["fix_bug"],
    default_read_path="examples/coding-agent/verify_sample.txt",
)

agent = (
    AgentBuilder("coding-agent-real")
    .with_kernel_defaults()
    .with_tools(*tools)
    .with_planner(planner)
    .with_event_log(LocalEventLog(path=".dare/examples/coding-agent/real/event_log.jsonl"))
    .with_checkpoint_dir(".dare/examples/coding-agent/real/checkpoints")
    .build()
)

result = await agent.run("搜索 TODO 并总结")
print(result.success)
print(result.output)
```

## 可选参数说明

- `plan_steps`：显式传入固定计划步骤（用于测试与回归）
- `event_log_path` / `checkpoint_dir`：指定审计与断点输出路径

## 注意事项

- `run_tests` 工具调用 `pytest`，需要环境中已安装 pytest
- `read_file` / `write_file` 都限制在 `workspace` 目录内
- `edit_line` 会修改文件内容，配合任务示例可实现“临时插入 + 删除”

---

*这个示例与框架同步开发，用于验证设计决策。*
