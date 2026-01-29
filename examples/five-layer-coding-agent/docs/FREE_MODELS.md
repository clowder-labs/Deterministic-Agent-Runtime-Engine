# OpenRouter 免费模型指南

## 推荐模型列表

OpenRouter 提供多个免费模型用于测试。如果某个模型被限流，可以尝试其他模型。

### 🌟 推荐（编码任务）

| 模型 | ID | 特点 | 状态 |
|------|-------|------|------|
| **Qwen3 Coder** | `qwen/qwen3-coder:free` | 专为编码设计，速度快 | ⚠️ 可能限流 |
| **Gemini Flash** | `google/gemini-flash-1.5-8b-exp-0827:free` | 质量好，稳定性高 | ✅ 推荐 |
| **Llama 3.2** | `meta-llama/llama-3.2-3b-instruct:free` | 小型模型，速度快 | ✅ 稳定 |

### 🔄 备选方案

如果上述模型都被限流，可以尝试：

1. **等待一段时间**（通常几分钟后恢复）
2. **切换模型**（见下方完整列表）
3. **使用自己的 API key**（添加到 OpenRouter 账户）

## 如何切换模型

### 方法 1: 修改 .env 文件

```bash
# 编辑 .env 文件
nano .env

# 修改这一行：
OPENROUTER_MODEL=google/gemini-flash-1.5-8b-exp-0827:free
```

### 方法 2: 使用环境变量

```bash
OPENROUTER_MODEL=google/gemini-flash-1.5-8b-exp-0827:free \
PYTHONPATH=../.. python openrouter_agent.py
```

## 完整免费模型列表

### 编码能力强

```
qwen/qwen3-coder:free
```

### 通用能力强

```
google/gemini-flash-1.5-8b-exp-0827:free
meta-llama/llama-3.2-3b-instruct:free
meta-llama/llama-3.1-8b-instruct:free
google/gemini-flash-1.5:free
```

### 对话能力强

```
meta-llama/llama-3.2-3b-instruct:free
google/gemma-2-9b-it:free
```

## 常见问题

### Q: 为什么会被限流？

**A**: 免费模型是共享资源，使用量大时会触发限流保护。这是正常现象。

### Q: 如何避免限流？

**A**:
1. 使用高峰期外的时间测试
2. 添加自己的 API key 到 OpenRouter
3. 使用付费模型（成本很低，按用量计费）

### Q: 限流会持续多久？

**A**: 通常 1-5 分钟即可恢复。如果着急，可以切换到其他模型。

### Q: 交互式 CLI 支持自动 fallback 吗？

**A**: 是的！当 LLM 调用失败时，会自动使用基于关键词的 fallback plan，确保任务能继续执行。

## 推荐使用策略

### 演示场景
- 首选：`google/gemini-flash-1.5-8b-exp-0827:free`（稳定性高）
- 备选：`meta-llama/llama-3.2-3b-instruct:free`

### 开发测试
- 首选：`qwen/qwen3-coder:free`（编码能力强）
- 备选：确定性模式（无需 API）

### 持续集成 (CI)
- 推荐：确定性模式（`deterministic_agent.py` 或 `scenarios.py`）
- 原因：无 API 依赖，不受限流影响

## 获取更多信息

- OpenRouter 模型列表: https://openrouter.ai/models
- 免费模型实时状态: https://openrouter.ai/models?free=true
- API Keys: https://openrouter.ai/keys

---

**提示**: 对于生产环境，建议使用付费模型并添加自己的 API key，以获得更好的稳定性和速度。
