# Module: memory / knowledge

> Status: aligned to `dare_framework/memory` + `dare_framework/knowledge` (2026-01-31). TODO indicates gaps vs desired architecture.

## 1. 定位与职责

- 提供统一检索接口 `IRetrievalContext` 的具体实现（STM/LTM/Knowledge）。
- 作为 Context 的检索来源（短期/长期/知识库）。

## 2. 关键概念与数据结构

- `IRetrievalContext`：统一检索接口（Context kernel）。
- `IShortTermMemory`：短期记忆接口（可写）。
- `ILongTermMemory`：长期记忆接口（持久化）。
- `IKnowledge`：知识检索接口（RAG/GraphRAG 等）。
- `IKnowledgeTool`：Knowledge 作为 Tool 暴露的组合接口。

## 3. 当前实现

- `InMemorySTM`：默认短期记忆实现（内存列表）。
- LongTermMemory / Knowledge 仅有接口定义，缺少默认实现。

## 4. 与其他模块的交互

- **Context**：持有 STM/LTM/Knowledge 引用；`assemble()` 默认只取 STM。
- **Tool**：Knowledge 可作为 Tool 暴露（`IKnowledgeTool`）。
- **Model**：检索结果通过 Context 组装进入 ModelInput.messages。

## 5. 约束与限制

- 缺少默认 LTM/Knowledge 实现。
- 检索融合策略未标准化（默认 assemble 不合入 LTM/Knowledge）。

## 6. 扩展点

- 自定义 STM/LTM/Knowledge 实现，注入 Context。
- 自定义 `Context.assemble()` 以合并检索结果。

## 7. TODO / 未决问题

- TODO: 提供默认 LTM/Knowledge 实现（或接入外部向量库）。
- TODO: 统一检索融合策略（排序、去重、预算控制）。
- TODO: 知识作为 Tool 的统一策略（权限、计费、审计）。
