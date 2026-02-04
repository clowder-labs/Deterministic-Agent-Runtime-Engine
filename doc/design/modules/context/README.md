# Module: context

> Status: aligned to `dare_framework/context` (2026-01-31). TODO indicates gaps vs desired architecture.

## 1. 定位与职责

- Context-centric：Context 是核心实体，messages 在调用前按需组装。
- 持有 STM/LTM/Knowledge 引用 + Budget，用于上下文工程和预算控制。
- 输出 `AssembledContext`（messages + tools + metadata），供模型调用。

## 2. 关键概念与数据结构

- `Message`：统一消息结构（role/content/name/metadata）。
- `Budget`：资源预算与使用统计。
- `AssembledContext`：单次调用上下文（messages/tools/metadata/sys_prompt）。

## 3. 核心流程（当前实现）

- `Context.stm_add()`：写入短期记忆（STM）。
- `Context.listing_tools()`：通过 ToolProvider 获取 tool defs（结构化，内部缓存）。
- `Context.assemble()`：
  - 读取 STM 消息
  - 读取 tool defs
  - 组合为 `AssembledContext(messages, tools, metadata)`

> 现状说明：默认 assemble 仅使用 STM + tool listing；LTM/Knowledge 需自定义 Context 扩展（TODO）。

## 4. 关键接口与实现

- Kernel：`IContext`, `IRetrievalContext`（`dare_framework/context/kernel.py`）
- 默认实现：`Context`（`dare_framework/context/_internal/context.py`）

## 5. 与其他模块的交互

- **Agent**：写入 STM（user/assistant/tool），调用 `assemble()`。
- **Tool**：Context 通过 ToolProvider/ToolManager 输出 tool defs。
- **Memory/Knowledge**：Context 持有 retrieval 引用；当前默认 STM 为 `InMemorySTM`。
- **Model**：Agent 使用 `AssembledContext` 构造 `ModelInput`。

## 6. 约束与限制（当前实现）

- **工具列表缓存**：`Context` 内部缓存 tool defs，刷新时依赖 ToolProvider；未记录快照用于审计（TODO）。
- **检索融合缺失**：LTM/Knowledge 未默认合入 messages（TODO）。
- **Budget 仅局部使用**：Agent 侧使用 Budget，但缺少统一归因与跨组件统计（TODO）。

## 7. 扩展点

- 自定义 Context：覆盖 `assemble()` / `compress()`，实现检索融合、摘要压缩。
- 自定义 Retrieval：实现 `IRetrievalContext.get()` 作为 LTM/Knowledge。
- Tool listing：注入自定义 `IToolProvider`。

## 8. TODO / 未决问题

- TODO: 规范 `AssembledContext.metadata` 最小字段（context_id / tool_snapshot_hash）。
- TODO: 定义 LTM/Knowledge 融合策略与预算归因。
- TODO: 对齐工具快照记录与 EventLog 审计链。

## 9. Design Clarifications (2026-02-03)

- Doc gap: `Context` maintains skill state (`current_skill`), but skill injection path is not documented.
- Type cleanup: replaced string annotations with direct types + `TYPE_CHECKING` imports.
- Config snapshot: `Context.config` is intended as read‑only session snapshot (no `config_update`).
