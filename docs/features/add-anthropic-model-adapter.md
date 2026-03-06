---
change_ids: ["add-anthropic-model-adapter"]
doc_kind: feature
topics: ["model", "anthropic", "adapter", "cli-doctor"]
created: 2026-03-05
updated: 2026-03-05
status: active
mode: openspec
---

# Feature: add-anthropic-model-adapter

## Scope
新增独立 `AnthropicModelAdapter`，对接 Anthropic 官方 Messages API，并在 runtime/CLI 侧完成 `anthropic` adapter 的加载与诊断接入，不改造既有 OpenAI/OpenRouter adapter 内部实现。

## OpenSpec Artifacts
- Proposal: `openspec/changes/add-anthropic-model-adapter/proposal.md`
- Design: `openspec/changes/add-anthropic-model-adapter/design.md`
- Specs:
  - `openspec/changes/add-anthropic-model-adapter/specs/anthropic-model-adapter/spec.md`
- Tasks: `openspec/changes/add-anthropic-model-adapter/tasks.md`

## Progress
- 已完成：Anthropic adapter 代码、manager 接入、CLI doctor 接入、依赖与文档更新。
- 已完成：定向单测回归通过。
- 待完成：评审链接与归档动作。

## Evidence

### External References
- Anthropic Messages API: `https://docs.anthropic.com/en/api/messages`
- Anthropic tool use examples: `https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview`
- OpenRouter Anthropic Opus model page: `https://openrouter.ai/anthropic/claude-opus-4.1`
- OpenRouter Anthropic Sonnet model page: `https://openrouter.ai/anthropic/claude-sonnet-4.5`

### Commands
- `openspec new change "add-anthropic-model-adapter"`
- `openspec status --change "add-anthropic-model-adapter" --json`
- `.venv/bin/pytest -q tests/unit/test_anthropic_model_adapter.py tests/unit/test_default_model_adapter_manager.py tests/unit/test_client_cli.py`

### Results
- OpenSpec change 创建成功（schema: `spec-driven`）。
- Anthropic adapter 目标测试集通过：`74 passed, 1 warning`。

### Contract Delta
- schema: `changed`（新增 `anthropic` adapter 选择与请求/响应规范化行为，模型名为配置直传）。
- error semantics: `changed`（`anthropic` SDK 缺失时新增明确错误提示）。
- retry: `none`（reason: Anthropic adapter 本次仅做请求参数和响应解析适配，未引入新重试策略）。

### Golden Cases
- `tests/unit/test_anthropic_model_adapter.py`
- `tests/unit/test_default_model_adapter_manager.py`
- `tests/unit/test_client_cli.py`

### Regression Summary
- runner: `.venv/bin/pytest -q tests/unit/test_anthropic_model_adapter.py tests/unit/test_default_model_adapter_manager.py tests/unit/test_client_cli.py`
- summary: pass=74, fail=0, skip=0；覆盖新增 adapter 的序列化、模型名直传、manager 选择与 CLI doctor 诊断分支。

### Observability and Failure Localization
- start: adapter 初始化入口为 `DefaultModelAdapterManager.load_model_adapter(config)`，关键定位字段包含 `run_id` 与 `trace_id`。
- tool_call: `AnthropicModelAdapter._serialize_system_and_messages` 处理 tool_use/tool_result，关键定位字段包含 `tool_call_id`、`capability_id`、`attempt`。
- end: `client.messages.create(**params)` 返回后经 `_extract_response_text` / `_extract_tool_calls` / `_extract_usage` 归一化并结束本次推理链路。
- fail: `_build_client` 缺依赖或缺 API key/model 时抛错；`build_doctor_report` 提供依赖与密钥诊断，错误定位语义包含 `error_type` / `error_code` / `ToolResult.error`。

### Structured Review Report
- Changed Module Boundaries / Public API: 新增 `dare_framework/model/adapters/anthropic_adapter.py`，并在 `model/adapters/__init__.py`、`model/__init__.py`、`DefaultModelAdapterManager` 暴露 `anthropic` adapter 入口。
- New State: 无新增全局可变状态；adapter 仅维护 lazy 初始化的 SDK client 引用。
- Concurrency / Timeout / Retry: 复用 async SDK 调用路径；未新增 timeout/retry 语义，保持现有 runtime 并发模型不变。
- Side Effects and Idempotency: 仅新增 `anthropic` 依赖与 provider 分支；消息序列化与响应解析均为纯转换逻辑，幂等性不变。
- Coverage and Residual Risk: 相关单测已覆盖 adapter 载入、模型名直传、tool 序列化、doctor 诊断；残余风险是运行时配置错误（缺 model 或 key）导致初始化失败。

### Behavior Verification
- Happy path:
  - `adapter=anthropic` 时可加载 Anthropic adapter 并完成消息/工具块序列化与响应归一化。
  - 显式模型名（例如 `claude-sonnet-4-5`）会原样透传到 Anthropic SDK。
- Error branch:
  - 缺少 `ANTHROPIC_API_KEY` 或 `api_key` 时抛出显式错误。
  - 缺少 `Config.llm.model` 且 `ANTHROPIC_MODEL` 未设置时抛出模型必填错误。
  - doctor 在 `adapter=anthropic` 且未安装 `anthropic` SDK 时输出依赖告警。

### Risks and Rollback
- 风险：运行配置缺少模型名会导致 adapter 初始化失败。
- 回滚：删除 `anthropic` 分支与新增 adapter 文件即可恢复至原行为，不影响 OpenAI/OpenRouter 路径。

### Review and Merge Gate Links
- Intent PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/126`
- Implementation PR: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/199`
- Review request: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/199#pullrequestreview-3894789081`
- Merge gate: `https://github.com/zts212653/Deterministic-Agent-Runtime-Engine/pull/199/checks`
