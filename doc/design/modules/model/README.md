# Module: model

> Status: aligned to `dare_framework/model` (2026-01-31). TODO indicates gaps vs desired architecture.

## 1. 定位与职责

- 统一模型调用入口（`IModelAdapter.generate(...)`）。
- 定义运行时模型输入 `ModelInput(messages + tools + metadata)`。
- 提供 Prompt 管理与解析（见 `Model_Prompt_Management.md`）。

## 2. 关键概念与数据结构

- `ModelInput`：运行时模型请求结构（messages/tools/metadata）。
- `ModelResponse`：模型输出，包含 content 与 tool_calls。
- `GenerateOptions`：模型生成参数（temperature/max_tokens/etc）。
- `Prompt`：Prompt 定义（prompt_id/role/content/supported_models/order）。

## 3. 关键接口与实现

- Kernel：`IModelAdapter`（`dare_framework/model/kernel.py`）
- Manager：`IModelAdapterManager`, `IPromptLoader`, `IPromptStore`（`dare_framework/model/interfaces.py`）
- 默认管理器：`DefaultModelAdapterManager`（OpenAI/OpenRouter）
- Prompt Store：`LayeredPromptStore` + loaders

## 4. 内置适配器（当前实现）

- `OpenAIModelAdapter`（LangChain，支持工具调用）
- `OpenRouterModelAdapter`（OpenAI SDK 兼容接口）

> 现状说明：流式输出与多模型路由未实现（TODO）。

## 5. 与其他模块的交互

- **Context**：Context.assemble() 提供 messages/tools；Agent 负责构造 ModelInput。
- **Tool**：ModelResponse.tool_calls 触发 Tool Loop。
- **Config**：`Config.llm` 决定默认 adapter 与连接参数。

## 6. 约束与限制（当前实现）

- Prompt Store 默认按 workspace → user → built-in 的层级解析。
- Prompt 不支持热更新；需重新构造 PromptStore（TODO: reload）。
- Tool defs 需满足 OpenAI function-call 格式；adapter 做轻量兼容转换。

## 7. 扩展点

- 新增 ModelAdapter：实现 `IModelAdapter` 并注入 Manager。
- 新增 PromptLoader：加载远端或自定义 manifest。
- Prompt 版本策略：通过 `Prompt.version` + Store 选择逻辑扩展。

## 8. TODO / 未决问题

- TODO: 流式输出与增量 tool calls 支持。
- TODO: 多模型策略（fallback/router/ensemble）。
- TODO: Prompt 多阶段（plan/execute/verify）与上下文预算联动。
