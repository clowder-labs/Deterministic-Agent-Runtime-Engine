# Change: Refactor agent builders for config+manager resolution

## Why
当前 `dare_framework/builder/builder.py` 的 `AgentBuilder.build()` 强制要求显式提供 `IModelAdapter`（否则直接报错），且没有使用 `Config` 或各域的 `*Manager` 接口来加载缺失组件。这导致：

- 无法做到“builder 显式注入优先，否则按 config 通过 manager 自动补全”的确定性装配流程。
- builder 仅能构建 `SimpleChatAgent`，无法用一致的 builder 形态构建 `FiveLayerAgent`（五层运行时所需的 planner/validator/remediator/hooks 等更无法通过 manager 注入）。
- 多加载组件（tools/hooks/validators）在 API 语义上缺少明确的“extend/merge”约定与命名（`add_*` vs `with_*`）。

## What Changes
- 引入“内部基类 builder + 两个外部 builder 变体”的抽象：
  - `SimpleChatAgentBuilder`：构建 `SimpleChatAgent`
  - `FiveLayerAgentBuilder`：构建 `FiveLayerAgent`
- 统一装配规则（deterministic precedence）：
  - **builder 显式注入优先**：显式注入的组件永远覆盖/优先于 manager 产出的组件。
  - **缺省走 manager**：builder 未设置的组件，通过对应域的 manager + `Config` 来加载（例如 model 未指定则调用 `IModelAdapterManager.load_model_adapter(config=Config)`）。
  - **多加载使用 extend**：tools/hooks/validators 等多加载组件采用 “builder 显式 + manager 加载” 的 merge/extend 语义。
  - **config 只影响 manager 部分**：enable/disable 等 config 过滤仅作用于 manager 加载出的组件集合，不影响 builder 显式注入集合。
- 提供统一的 builder 选择入口（facade），例如 `Builder.simple_chat_agent_builder(name)` / `Builder.five_layer_agent_builder(name)`。
- builder API 对 multi-load 类别采用 `add_*` 命名（例如 `add_tools/add_hooks/add_validators`）来表达“extend”语义，避免 `with_*` 造成的覆盖歧义。
- 简化配置接口：移除 `ConfigSnapshot`，`IConfigProvider.current()/reload()` 直接返回不可变 `Config`。

## Impact
- Affected specs: `interface-layer`（Developer API / builders）, `component-management`（生命周期/注入边界）。
- Affected code (apply stage): `dare_framework/builder/*`、可能涉及 `dare_framework/agent/_internal/five_layer.py` 的 ToolGateway 调用签名对齐，以及新增/调整单元测试与示例。
 - Affected config surface: `dare_framework/config/kernel.py`, `dare_framework/config/types.py`, `dare_framework/config/_internal/file_config_provider.py`.

## Non-Goals (this change)
- 不在本变更中强制实现 entrypoint discovery 的默认 manager（builder 只消费 manager 接口；manager 的 discovery/selection 细节可由后续实现或外部注入提供）。
 - 不在本变更中引入新的 config 元数据机制（例如 hash/source layers）；如未来需要，可在 `IConfigProvider` 上扩展或引入新的 metadata 类型。
