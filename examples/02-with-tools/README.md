# 02-with-tools

带工具的 Agent 示例，展示如何使用 `add_tools()` 添加文件操作能力。

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

```python
agent = (
    BaseAgent.simple_chat_agent_builder("tool-agent")
    .with_model(model_adapter)
    .add_tools(ReadFileTool(), WriteFileTool(), SearchCodeTool())
    .build()
)
```

## Prompt 管理

系统提示由框架 Prompt Store 管理（默认 `base.system`），无需在示例中手写系统提示。

## 工具命名规则

工具 `name` 是唯一主键（capability id）。自定义工具时必须保证名称唯一。

## 执行模式

ReAct 模式：Reason → Act → Observe 循环

## 适用场景

- 文件操作
- 代码搜索
- 简单自动化
