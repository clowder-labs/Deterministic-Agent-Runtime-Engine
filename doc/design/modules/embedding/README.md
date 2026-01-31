# Module: embedding

> Status: aligned to `dare_framework/embedding` (2026-01-31). TODO indicates gaps vs desired architecture.

## 1. 定位与职责

- 提供文本向量化能力接口（embedding adapter）。
- 供知识检索 / RAG / 语义匹配等模块使用。

## 2. 关键概念与数据结构

- `EmbeddingResult`：向量 + metadata。
- `EmbeddingOptions`：embedding 参数（model/metadata）。
- `IEmbeddingAdapter`：embedding 适配器接口。

## 3. 当前实现

- `OpenAIEmbeddingAdapter`（LangChain OpenAIEmbeddings）。

## 4. 与其他模块的交互

- **Knowledge**：知识检索可调用 embedding 生成向量（当前未接入）。
- **Config**：embedding 尚未纳入 Config 管理（TODO）。

## 5. 约束与限制

- 依赖 `langchain-openai`，未提供 fallback。
- 无 Manager / Factory 统一选择逻辑（TODO）。

## 6. 扩展点

- 实现新的 embedding adapter（本地模型/第三方 API）。
- 增加 Manager/Factory 统一管理。

## 7. TODO / 未决问题

- TODO: 接入 Knowledge/RAG pipeline。
- TODO: 统一配置与 adapter 选择策略。
