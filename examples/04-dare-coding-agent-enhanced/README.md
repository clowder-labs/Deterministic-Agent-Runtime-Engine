# 04-dare-coding-agent-enhanced

使用 `DareAgentBuilder` 演示完整五层循环，并提供可演示的交互式 CLI。本示例同时集成**本地 MCP 服务**作为 tool，以及 **Knowledge（rawdata 内存存储）**：Agent 可调用 MCP 工具（如 `local_math:add`）和知识库工具 `knowledge_get` / `knowledge_add`。MCP 服务由本仓库自带的 Python 脚本实现，无需 Node/npx。

## 快速开始

```bash
# 进入目录
cd examples/04-dare-coding-agent-enhanced

# 配置环境（OpenRouter）
cp .env.example .env
# 编辑 .env 添加你的 OPENROUTER_API_KEY

# 运行交互式 CLI
python main.py
```

默认模型使用 `OPENROUTER_MODEL`，未设置时默认为 `z-ai/glm-4.7`。
若账号 credits 较少，建议设置 `OPENROUTER_MAX_TOKENS=2048`。
如需限制请求时间，可设置 `OPENROUTER_TIMEOUT=60`（秒）。

## CLI 用法

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

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Session Loop (跨 Context Window)                                │
│  └─ Milestone Loop (Observe → Plan → Execute → Verify)           │
│     ├─ Plan Loop (生成证据型计划)                                 │
│     ├─ Execute Loop (LLM 驱动执行)                               │
│     └─ Tool Loop (工具调用)                                       │
└─────────────────────────────────────────────────────────────────┘
```

## 核心代码（简化）

```python
from dare_framework.knowledge import RawDataKnowledge, InMemoryRawDataStorage

knowledge = RawDataKnowledge(storage=InMemoryRawDataStorage())
agent = (
    DareAgentBuilder("dare-coding-agent")
    .with_model(OpenRouterModelAdapter(...))
    .with_knowledge(knowledge)
    .add_tools(ReadFileTool(), WriteFileTool(), SearchCodeTool(), RunCommandTool())
    .with_planner(DefaultPlanner(model))
    .add_validators(FileExistsValidator(workspace))
    .with_remediator(DefaultRemediator(model))
    .build()
)
```

## Skill 挂载

一个 agent 同时只支持一个 skill。框架支持：

- **Builder**：`.with_skill(path)` 设置初始 skill
- **Config**：`initial_skill_path` 设置初始 skill
- **运行时**：`agent.set_skill(skill)` / `agent.clear_skill()` 动态挂载、替换、删除

Skill prompt 在 context.assemble() 时作为单独一段注入，与 base prompt 解耦。

示例 CLI 通过 `--skill` 传入路径：

```bash
python cli.py --skill path/to/my_skill
```

Skill 目录结构（Agent Skills 格式）：

```
my_skill/
├── SKILL.md        # YAML frontmatter + markdown 正文
└── scripts/        # 可执行脚本
    ├── run_tool.py
    └── check.sh
```

## Prompt 管理说明

系统提示由框架 Prompt Store 管理（默认 `base.system`），并自动合并 skill 内容。
如需覆盖，使用 `.dare/_prompts.json` 配置。

## Knowledge（本示例）

本示例使用 **rawdata 知识库 + 内存存储**（`RawDataKnowledge(storage=InMemoryRawDataStorage())`），Agent 可通过工具调用知识库：

| 工具名 | 说明 |
|--------|------|
| `knowledge_get` | 按查询字符串检索知识，参数 `query`（必填）、`top_k`（可选，默认 5），返回匹配的文档列表。 |
| `knowledge_add` | 向知识库添加内容，参数 `content`（必填）、`metadata`（可选）。 |

知识库与本地工具、MCP 工具一起注册到工具列表，可在任务中直接让 Agent 调用（例如：「把这句话记到知识库」或「从知识库查一下和 Python 相关的内容」）。

## 工具命名规则

工具 `name` 是唯一主键（capability id）。自定义工具时必须保证名称唯一。

## MCP 本地服务（本示例）

本示例在 `.dare/mcp/` 下配置了**本地 MCP 服务**，Agent 通过 HTTP 连接该服务并调用其工具。服务需**你先单独启动**，再启动 CLI，这样才是“真正的服务”形态。

### 配置

- **目录**：`04-dare-coding-agent-enhanced/.dare/mcp/`
- **当前配置**：`local_math.json` — HTTP 连接 `http://127.0.0.1:8765/`（服务需先在本机启动）。

### 本地 MCP 服务实现

- **脚本**：`local_mcp_server.py` — 以 HTTP 方式提供 MCP 协议，暴露四个工具：`add`（加）、`subtract`（减）、`multiply`（乘）、`divide`（除），用于验证「一个服务提供多个 tool」。
- **依赖**：仅标准库，与 Agent 同环境 Python 即可。
- **启动方式**：**你先在终端 1 运行服务**，再在终端 2 运行 CLI：

  ```bash
  # 终端 1：先启动 MCP 服务（默认监听 127.0.0.1:8765）
  cd examples/04-dare-coding-agent-enhanced
  python local_mcp_server.py

  # 终端 2：再启动 Agent/CLI，会连接该服务
  cd examples/04-dare-coding-agent-enhanced
  python main.py
  ```

### 提供的 MCP 工具（local_math 服务器，一个服务四个 tool）

| 工具名 | 说明 |
|--------|------|
| `local_math:add` | 两数相加，参数 `a`、`b`，返回和。 |
| `local_math:subtract` | 两数相减，返回 a - b。 |
| `local_math:multiply` | 两数相乘，返回积。 |
| `local_math:divide` | 两数相除，返回 a / b；b 为 0 时返回错误。 |

启动 CLI 时若看到 `MCP tools loaded: N`，即表示 MCP 已加载，可直接在任务中让 Agent 调用（例如：「用 local_math 的 add 工具算 17+25」）。

在 `dare>` 后直接输入任务即可，例如：「用 local_math 的 add 工具算 17+25」或「用 local_math 的 multiply 算 17×25」。

### 自定义 MCP 配置

在 `.dare/mcp/` 下新增或修改 JSON 文件即可，支持单服务或多服务格式。详见框架 [MCP 文档](../../dare_framework/mcp/)。

## 文件结构

```
04-dare-coding-agent-enhanced/
├── main.py
├── cli.py
├── demo.py
├── demo_script.txt
├── local_mcp_server.py      # 本地 MCP 服务（add/subtract/multiply/divide，纯 Python）
├── .dare/
│   └── mcp/
│       └── local_math.json   # 本地 MCP 服务配置（四则运算）
├── validators/
│   └── file_validator.py
├── workspace/
└── README.md
```
