# 04-dare-coding-agent

在 01–03 基础上加入完整五层循环、计划/执行模式与验证修复流程，提供可演示的交互式 CLI。

## 运行

```bash
cd examples/04-dare-coding-agent
export OPENROUTER_API_KEY="your-api-key"
# 可选：指定模型
export OPENROUTER_MODEL="z-ai/glm-4.7"
# 可选：限制最大输出 tokens，避免信用不足错误
export OPENROUTER_MAX_TOKENS="2048"
# 可选：限制请求时间（秒）
export OPENROUTER_TIMEOUT="60"
python main.py
```

默认模型使用 `OPENROUTER_MODEL`，未设置时默认为 `z-ai/glm-4.7`。
若账号 credits 较少，建议设置 `OPENROUTER_MAX_TOKENS=2048`。
如需限制请求时间，可设置 `OPENROUTER_TIMEOUT=60`（秒）。

### CLI 用法

交互命令：
- `/mode plan`：计划预览模式（先生成计划，等待 /approve 执行）
- `/mode execute`：直接执行模式（ReAct）
- `/approve`：执行当前待审批计划
- `/reject`：取消当前计划
- `/status`：查看状态
- `/help`：帮助
- `/quit`：退出

### 演示脚本

一键演示（推荐给演示场景）：

```bash
python cli.py --demo demo_script.txt
# 或
python demo.py
```

## 代码要点

```python
agent = (
    DareAgentBuilder("dare-coding-agent")
    .with_model(OpenRouterModelAdapter(...))
    .add_tools(ReadFileTool(), WriteFileTool(), SearchCodeTool(), RunCommandTool())
    .with_planner(DefaultPlanner(model))
    .add_validators(FileExistsValidator(workspace))
    .with_remediator(DefaultRemediator(model))
    .build()
)
```

## 进阶点

- 相对前面示例，新增完整五层循环（Session → Milestone → Plan/Execute → Tool）
- 计划预览与审批：`/mode plan` + `/approve`；直接执行：`/mode execute`
- 引入验证与修复流程：Validator + Remediator
- 工具 `name` 为唯一 capability id，自定义工具需保证名称唯一

**架构（五层循环）**

```
┌─────────────────────────────────────────────────────────────────┐
│  Session Loop (跨 Context Window)                                │
│  └─ Milestone Loop (Observe → Plan → Execute → Verify)           │
│     ├─ Plan Loop (生成证据型计划)                                 │
│     ├─ Execute Loop (LLM 驱动执行)                               │
│     └─ Tool Loop (工具调用)                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Prompt 管理

系统提示由框架 Prompt Store 管理（默认 `base.system`），无需在示例中手写系统提示。
如需覆盖，使用 `.dare/_prompts.json` 配置。

## 文件结构

```
04-dare-coding-agent/
├── main.py
├── cli.py
├── demo.py
├── demo_script.txt
├── validators/
│   └── file_validator.py
├── workspace/
└── README.md
```

## 适用场景

- 复杂任务拆解与执行
- 带审批的自动化流程
- 演示五层循环与验证修复机制
