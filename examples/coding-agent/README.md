# Example: Coding Agent

这是一个与当前 DARE Framework 设计对齐的 Coding Agent 示例，用于验证核心循环与组件装配。

## 目的

1. **验证框架设计** - 覆盖 Plan/Execute/Tool Loop 与证据闭环
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

1. **Plan Tool 语义**  
   `FixBugSkill` 作为 Plan Tool，用于触发“遇到计划工具 → 重新规划”的路径。

2. **执行边界与完成条件**  
   `DemoPlanGenerator` 为部分步骤附加 `Envelope` 与 `DonePredicate`，验证证据闭环。

3. **可审计性**  
   示例可配置 EventLog 与 Checkpoint 路径，用于验证事件链与断点保存。

4. **确定性模式**  
   `mock_mode=True` 时使用确定性计划生成器，避免外部依赖。

## 使用方式（代码侧）

在示例目录中运行时可直接导入：

```python
from agent import CodingAgent
from dare_framework.core.models.plan import ProposedStep
from dare_framework.core.models.runtime import new_id

steps = [
    ProposedStep(step_id=new_id("step"), tool_name="read_file", tool_input={"path": "README.md"})
]

agent = CodingAgent(
    workspace=".",
    mock_mode=True,
    plan_steps=steps,
)

result = await agent.run("读取 README.md 并解释内容")
print(result.success)
print(result.output)
```

## 使用 OpenAI 真实模型

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
from agent import CodingAgent
from openai_adapter import OpenAIModelAdapter, OpenAIPlanGenerator, tool_definitions_from_tools
from tools import ReadFileTool, WriteFileTool, SearchCodeTool, RunTestsTool

tools = [
    ReadFileTool(workspace="."),
    WriteFileTool(workspace="."),
    SearchCodeTool(workspace="."),
    RunTestsTool(),
]

adapter = OpenAIModelAdapter(model="gpt-4o-mini")
plan_generator = OpenAIPlanGenerator(
    model=adapter,
    tool_definitions=tool_definitions_from_tools(tools),
    plan_tools=["fix_bug"],
    default_read_path="examples/coding-agent/verify_sample.txt",
)

agent = CodingAgent(
    workspace=".",
    mock_mode=False,
    model_adapter=adapter,
    plan_generator=plan_generator,
)

# 如果只想让模型做计划、由运行时按计划执行工具：
# - mock_mode=True
# - 不传 model_adapter

result = await agent.run("搜索 TODO 并总结")
print(result.success)
print(result.output)
```

## 可选参数说明

- `mock_mode=True`：使用确定性计划生成器，默认开启
- `plan_steps`：显式传入固定计划步骤（用于测试与回归）
- `plan_generator`：传入自定义计划生成器（mock_mode 下也可用）
- `event_log_path` / `checkpoint_path`：指定审计与断点输出路径
- `demo_plan=False`：关闭演示型计划生成器，使用最小的默认计划

## 注意事项

- `run_tests` 工具调用 `pytest`，需要环境中已安装 pytest
- `read_file` / `write_file` 都限制在 `workspace` 目录内
- `edit_line` 会修改文件内容，配合任务示例可实现“临时插入 + 删除”

---

*这个示例与框架同步开发，用于验证设计决策。*
