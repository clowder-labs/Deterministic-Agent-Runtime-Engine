# 01-basic-chat

最简单的对话 Agent 示例，展示 `SimpleChatAgentBuilder` 的最小用法。

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

## Prompt 管理

系统提示由框架 Prompt Store 管理（默认 `base.system`），无需在示例中手写系统提示。
如需覆盖，使用 `.dare/_prompts.json` 配置。

## 适用场景

- 简单问答
- 对话机器人
- 快速原型
