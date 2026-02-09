# 02-with-tools

在 01 的基础上加入工具调用与 ReAct 循环，演示 `add_tools()` 与工作区限制。

## 运行

```bash
cd examples/02-with-tools
export OPENROUTER_API_KEY="your-api-key"
# 可选：指定模型
export OPENROUTER_MODEL="z-ai/glm-4.7"
# 可选：限制最大输出 tokens，避免信用不足错误
export OPENROUTER_MAX_TOKENS="2048"
python main.py
```

## 代码要点

本示例使用 **ReactAgent**（`react_agent_builder`），会执行模型的 tool_call 并循环直到模型返回最终文字；若用 `simple_chat_agent_builder` 则不会执行工具。

- 使用 `with_config(Config(workspace_dir=...))` 设置工具工作区根目录。

```python
agent = (
    BaseAgent.react_agent_builder("tool-agent")
    .with_model(model_adapter)
    .with_config(Config(workspace_dir=str(workspace)))
    .add_tools(ReadFileTool(), WriteFileTool(), SearchCodeTool())
    .build()
)
```

## 进阶点

- 相对 01，新增 ReAct 模式（Reason → Act → Observe），模型 tool_call 会被执行
- `with_config(Config(workspace_dir=...))` 限定工具工作区根目录
- 工具 `name` 为唯一 capability id，自定义工具需保证名称唯一

## Prompt 管理

系统提示由框架 Prompt Store 管理（默认 `base.system`），无需在示例中手写系统提示。
如需覆盖，使用 `.dare/_prompts.json` 配置。

## 文件结构

```
02-with-tools/
├── main.py
└── README.md
```

## 适用场景

- 文件操作
- 代码搜索
- 简单自动化
