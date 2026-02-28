## Context

在 FR-009/FR-011 完成后，模块测试锚点已经全量补齐，但 `memory_knowledge` 仍保留“缺失直连单测”的过渡声明（FR-GAP-011）。
本次变更目标是把该项从“过渡态”推进到“闭环态”。

## Goals / Non-Goals

**Goals:**
- 为 memory/knowledge 域建立可稳定执行的直连单测基线。
- 将模块文档测试锚点从“组合验证 + 缺失声明”改为“直连测试锚点”。
- 完成 FR-012/T6-5 台账闭环。

**Non-Goals:**
- 不改动 memory/knowledge 运行时业务行为。
- 不扩展向量检索策略、RAG 算法或跨域融合逻辑。

## Decisions

1. 测试聚焦 rawdata/in-memory 路径，避免外部依赖（SQLite/Chroma/网络）造成不稳定。
2. 直连单测覆盖两类入口：
   - 工厂层：`create_long_term_memory` / `create_knowledge`
   - 默认实现层：`RawDataLongTermMemory` / `RawDataKnowledge`
3. 验证重点为“契约正确性”：输入配置、持久化/检索语义、缺失 embedding 时的降级返回。

## Risks / Trade-offs

- [风险] 仅覆盖 rawdata 基线，vector 路径仍主要依赖现有组合验证。
  → Mitigation: 保留后续增量任务，按依赖成熟度追加 vector 直连测试。
- [风险] 测试断言过度绑定实现细节会提升维护成本。
  → Mitigation: 以接口行为为主，不断言内部私有实现细节。
