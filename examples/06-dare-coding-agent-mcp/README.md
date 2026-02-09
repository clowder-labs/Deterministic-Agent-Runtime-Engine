# 06-dare-coding-agent-mcp

基于 `04-dare-coding-agent` 增加 MCP 集成，演示：
- MCP 通过配置文件加载（`.dare/config.json` + `.dare/mcp/*.json`）
- Agent 如何同时使用本地工具和 MCP 工具
- 运行时动态注册/重载 MCP（无需重启 CLI）

## 当前是否有“默认 MCP”

- 框架有 **MCP 默认实现**（client/loader/factory/provider），位于 `dare_framework.mcp.defaults`。
- 但没有“默认内置 MCP 服务”。
- 要真正可用，仍需你在配置里声明 MCP server（本示例已提供）。

## 运行

```bash
cd examples/06-dare-coding-agent-mcp
export OPENROUTER_API_KEY="your-api-key"
# 可选
export OPENROUTER_MODEL="z-ai/glm-4.7"
export OPENROUTER_MAX_TOKENS="2048"
export OPENROUTER_TIMEOUT="60"
```

终端 1：启动本地 MCP 服务

```bash
python local_mcp_server.py
```

终端 2：启动 Agent CLI

```bash
python main.py
```

## MCP 配置（config 驱动）

本示例通过 `.dare/config.json` 加载 MCP：

```json
{
  "mcp_paths": [
    ".dare/mcp"
  ],
  "allowmcps": [
    "local_math"
  ]
}
```

MCP server 定义在 `.dare/mcp/local_math.json`：

```json
{
  "name": "local_math",
  "transport": "http",
  "url": "http://127.0.0.1:8765/",
  "timeout_seconds": 30,
  "enabled": true
}
```

## CLI 命令

- `/mode plan`：计划预览模式（先生成计划，等待 `/approve`）
- `/mode execute`：直接执行模式
- `/approve`：执行待审批计划
- `/reject`：取消待审批计划
- `/status`：查看当前状态
- `/mcp list`：查看 MCP 与本地工具列表
- `/mcp inspect [tool_name]`：打印当前暴露给模型的 MCP tool schema（可选指定单个工具）
- `/mcp reload [paths...]`：运行时重载 MCP（默认读取最新 config，也可临时传路径）
- `/mcp unload`：卸载当前 MCP provider
- `/help`：帮助
- `/quit`：退出

## 动态注册 MCP 怎么做

1. 新增或修改 `.dare/mcp/*.json`（例如再加一个 server 配置）。
2. 在 CLI 执行 `/mcp reload`。
3. 用 `/mcp list` 确认新工具已出现。

如果你希望临时从其他目录加载 MCP 配置：

```text
/mcp reload /absolute/path/to/mcp
```

## 演示脚本

```bash
python cli.py --demo demo_script.txt
# 或
python demo.py
```

## 示例任务

- `用 local_math:add 工具计算 17 + 25，只返回数字结果`
- `用 local_math:multiply 计算 6 * 7`

## 文件结构

```text
06-dare-coding-agent-mcp/
├── main.py
├── cli.py
├── demo.py
├── demo_script.txt
├── local_mcp_server.py
├── .dare/
│   ├── config.json
│   └── mcp/
│       └── local_math.json
├── validators/
│   └── file_validator.py
├── workspace/
└── README.md
```
