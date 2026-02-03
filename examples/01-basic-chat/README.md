# 01-basic-chat

最小可运行对话 Agent。作为所有示例的起点，后续示例在此基础上逐步增加工具、可观测性与多层循环。

## 运行

```bash
cd examples/01-basic-chat
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
    BaseAgent.simple_chat_agent_builder("basic-chat")
    .with_model(model_adapter)
    .build()
)
result = await agent.run("Hello!")
```

## 进阶点

- 起点示例：最小化 Builder 链路（`simple_chat_agent_builder` + `with_model` + `build`）
- 不执行工具调用，仅返回文本响应

## Prompt 管理

系统提示由框架 Prompt Store 管理（默认 `base.system`），无需在示例中手写系统提示。
如需覆盖，使用 `.dare/_prompts.json` 配置。

## 文件结构

```
01-basic-chat/
├── main.py
└── README.md
```

## 适用场景

- 简单问答
- 对话机器人
- 快速原型
