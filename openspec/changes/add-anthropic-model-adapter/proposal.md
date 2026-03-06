## Why

当前框架仅内置 `openai` / `openrouter` 两类模型适配器，无法直接对接 Anthropic 官方 Messages API。用户明确需要独立 Anthropic adapter，并要求模型名由用户配置直传，避免因新模型发布而改代码。

## What Changes

- 新增独立 `AnthropicModelAdapter`，基于 Anthropic 官方 Python SDK 的 `messages.create` 接口实现。
- 在 adapter 内统一处理消息序列化（含 tool history / tool result）、响应反序列化（text/tool_use/thinking/usage）。
- 在 `DefaultModelAdapterManager` 增加 `anthropic` 分支，支持通过 `Config.llm.adapter="anthropic"` 加载。
- 在 CLI doctor 诊断中增加 `anthropic` adapter 的 API Key 与依赖检查。
- 更新 model/client 设计与使用文档，补充 Anthropic 配置与官方参考链接。

## Capabilities

### New Capabilities
- `anthropic-model-adapter`: Anthropic 官方 API 的模型适配能力（模型名直传，tool calling，usage/thinking 归一化）。

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `dare_framework/model/adapters/anthropic_adapter.py`
  - `dare_framework/model/adapters/__init__.py`
  - `dare_framework/model/__init__.py`
  - `dare_framework/model/default_model_adapter_manager.py`
  - `client/commands/info.py`
  - `client/main.py`
  - `pyproject.toml`
  - `requirements.txt`
- Affected tests:
  - `tests/unit/test_anthropic_model_adapter.py`
  - `tests/unit/test_default_model_adapter_manager.py`
  - `tests/unit/test_client_cli.py`
- New dependency:
  - `anthropic` (official SDK)
