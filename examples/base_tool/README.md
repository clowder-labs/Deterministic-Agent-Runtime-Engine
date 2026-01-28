# Example: Base Tool (v4.0)

该目录展示 v4.0 工具运行时的最小可运行示例（基于 Builder 组装），包括：
- 可信工具目录（Tool Gateway Registry）
- 内置文件工具集（read/search/write/edit）
- 通过大模型进行工具调用的最小闭环

## 目录结构

```
base_tool/
├── README.md           # 本文件
├── v4_tooling.py       # v4.0 工具运行时（Builder 组装后直接调用）
└── tool_chat3.4.py     # v4.0 工具调用（Builder 组装 + 模型驱动）
```

## 运行方式

### 1) 直接调用工具（不经过大模型）

```bash
PYTHONPATH=. python examples/base_tool/v4_tooling.py
```

可选环境变量：
- `TOOL_WORKSPACE_ROOT`：工作目录根（默认 `.`）
- `TOOL_READ_PATH`：示例读取文件路径（默认 `examples/base_tool/README.md`）
- `TOOL_LOG_LEVEL`：日志级别（默认 `INFO`）

### 2) 通过大模型调用工具（ReAct Loop）

```bash
PYTHONPATH=. python examples/base_tool/tool_chat3.4.py
```

可选环境变量：
- `CHAT_MODEL`：模型名（默认 `qwen-plus`）
- `CHAT_API_KEY`：API key
- `CHAT_ENDPOINT`：模型网关地址（默认 DashScope 兼容端点）
- `CHAT_LOG_LEVEL`：日志级别（默认 `INFO`）
- `TOOL_WORKSPACE_ROOT`：工作目录根（默认 `.`）

## 注意事项

- `tool_chat3.4.py` 依赖 `langchain-openai`（见 `requirements.txt`）
- `run_command` 为高风险工具；示例仅演示调用链，不包含审批流程
- 文件工具默认限制在 `workspace_roots` 内，且受 guardrails（max_bytes/max_results）约束
