# 05-dare-coding-agent-enhanced

在 04 的基础上加入本地 MCP 服务与 Knowledge（rawdata 内存存储），并支持 Skill 动态挂载。

## 运行

```bash
cd examples/05-dare-coding-agent-enhanced
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

### 启动本地 MCP 服务（体验 MCP 工具时必需）

```bash
# 终端 1：先启动 MCP 服务（默认监听 127.0.0.1:8765）
cd examples/05-dare-coding-agent-enhanced
python local_mcp_server.py

# 终端 2：再启动 Agent/CLI，会连接该服务
cd examples/05-dare-coding-agent-enhanced
python main.py
```

## 代码要点

```python
from dare_framework.knowledge import create_knowledge

knowledge = create_knowledge({"type": "rawdata", "storage": "in_memory"})
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

## 进阶点

- 相对 04，新增 Knowledge（rawdata + 内存存储）与 MCP 工具接入
- 支持 Skill 动态挂载（Builder / Config / 运行时）
- 继承 04 的五层循环与计划/执行模式

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

**Skill 挂载**

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

**Knowledge（本示例）**

本示例使用 **rawdata 知识库 + 内存存储**（`create_knowledge({"type": "rawdata", "storage": "in_memory"})`），Agent 可通过工具调用知识库：

| 工具名 | 说明 |
|--------|------|
| `knowledge_get` | 按查询字符串检索知识，参数 `query`（必填）、`top_k`（可选，默认 5），返回匹配的文档列表。 |
| `knowledge_add` | 向知识库添加内容，参数 `content`（必填）、`metadata`（可选）。 |

知识库与本地工具、MCP 工具一起注册到工具列表，可在任务中直接让 Agent 调用（例如：「把这句话记到知识库」或「从知识库查一下和 Python 相关的内容」）。

**MCP 本地服务（本示例）**

本示例在 `.dare/mcp/` 下配置了**本地 MCP 服务**，Agent 通过 HTTP 连接该服务并调用其工具。服务需**你先单独启动**，再启动 CLI。

配置与实现：

- **目录**：`05-dare-coding-agent-enhanced/.dare/mcp/`
- **当前配置**：`local_math.json` — HTTP 连接 `http://127.0.0.1:8765/`
- **脚本**：`local_mcp_server.py` — 以 HTTP 方式提供 MCP 协议，暴露 `add` / `subtract` / `multiply` / `divide`
- **依赖**：仅标准库，与 Agent 同环境 Python 即可

提供的 MCP 工具（local_math 服务器，一个服务四个 tool）：

| 工具名 | 说明 |
|--------|------|
| `local_math:add` | 两数相加，参数 `a`、`b`，返回和。 |
| `local_math:subtract` | 两数相减，返回 a - b。 |
| `local_math:multiply` | 两数相乘，返回积。 |
| `local_math:divide` | 两数相除，返回 a / b；b 为 0 时返回错误。 |

启动 CLI 时若看到 `MCP tools loaded: N`，即表示 MCP 已加载，可直接在任务中让 Agent 调用（例如：「用 local_math 的 add 工具算 17+25」）。

在 `dare>` 后直接输入任务即可，例如：「用 local_math 的 add 工具算 17+25」或「用 local_math 的 multiply 算 17×25」。

### 自定义 MCP 配置

在 `.dare/mcp/` 下新增或修改 JSON 文件即可，支持单服务或多服务格式。

## Prompt 管理

系统提示由框架 Prompt Store 管理（默认 `base.system`），并自动合并 skill 内容。
如需覆盖，使用 `.dare/_prompts.json` 配置。

## 文件结构

```
05-dare-coding-agent-enhanced/
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

## 适用场景

- 本地 MCP 服务与多工具协作验证
- Knowledge 读写与长期记忆实验
- 技能动态挂载与 CLI 演示
