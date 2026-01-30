# Example: Tool Manager

该目录按 Agent 类型拆分示例，展示工具运行时的最小可运行用法（基于 Builder 组装）：

- **SimpleChatAgent**：需要显式构建工具能力（`ToolManager` + `IToolProvider` 或 `register_tool`）
- **FiveLayerAgent**：Builder 会默认构建 `ToolManager` 作为网关，通常不需要自定义 `tool_gateway`（只需 `add_tools` + `with_config`）

## 目录结构

```
tool_manager/
├── README.md              # 本文件
├── simple_agent_tool_gateway.py            # SimpleChatAgent 直调用 + provider/direct 两种注册模式
└── five_layer_agent_tool_gateway_chat.py   # FiveLayerAgent + 默认网关 + 模型驱动
```

## 运行方式

### 1) SimpleChatAgent 直接调用工具（不经过大模型）

默认使用 provider 注册模式：

```bash
PYTHONPATH=. python examples/tool_manager/simple_agent_tool_gateway.py
```

使用 direct 注册模式（演示 register_tool）：

```bash
TOOL_REGISTRY_MODE=direct PYTHONPATH=. python examples/tool_manager/simple_agent_tool_gateway.py
```

可选环境变量：
- `TOOL_WORKSPACE_ROOT`：配置读取的 workspace 目录（默认 `.`）
- `TOOL_READ_PATH`：示例读取文件路径（默认 `examples/tool_manager/README.md`）
- `TOOL_LOG_LEVEL`：日志级别（默认 `INFO`）
- `TOOL_REGISTRY_MODE`：`provider` 或 `direct`（默认 `provider`）

模式说明：
- `provider`：通过 `register_provider` 批量同步工具，适合动态/远端工具源（如 MCP、配置驱动）。
- `direct`：通过 `register_tool` 逐个注册工具，适合少量固定工具，便于更新/禁用/移除。

### 2) FiveLayerAgent 通过大模型调用工具（ReAct Loop）

```bash
PYTHONPATH=. python examples/tool_manager/five_layer_agent_tool_gateway_chat.py
```

可选环境变量：
- `CHAT_MODEL`：模型名（默认 `qwen-plus`）
- `CHAT_API_KEY`：API key
- `CHAT_ENDPOINT`：模型网关地址（默认 DashScope 兼容端点）
- `CHAT_LOG_LEVEL`：日志级别（默认 `INFO`）

## 配置说明

工具运行时的配置来自 `.dare/config.json`（默认位于 workspace 目录内）。示例配置：

```json
{
  "workspace_dir": ".",
  "tools": {
    "read_file": {"max_bytes": 1000000},
    "write_file": {"max_bytes": 1000000},
    "edit_line": {"max_bytes": 1000000},
    "search_code": {
      "max_results": 50,
      "max_file_bytes": 1000000,
      "ignore_dirs": [".git", "node_modules", "__pycache__", ".venv", "venv"]
    }
  }
}
```

## 注意事项

- 原 `examples/tool-management` 示例已合并到本目录，统一以 IToolGateway 视角演示。
- LLM 接收到的工具名使用 `ITool.name`；`capability_id` 仅用于内部路由与审计。
- `five_layer_agent_tool_gateway_chat.py` 依赖 `langchain-openai`（见 `requirements.txt`）
- `run_command` 为高风险工具；示例仅演示调用链，不包含审批流程
- 文件工具默认限制在 `workspace_dir` 内，且受 guardrails（max_bytes/max_results）约束
