# Design TODO Index

> Status: generated from module docs (2026-02-05).
>
> 用途：集中查看当前架构/模块设计文档中的 TODO，便于分工与追踪。

## agent
- [ ] 将 ValidatedPlan.steps 驱动 Execute Loop（计划执行一致性）。(`docs/design/modules/agent/README.md`)
- [ ] 引入 plan attempt snapshot/rollback，实现失败计划隔离。(`docs/design/modules/agent/README.md`)
- [ ] 接入 `ISecurityBoundary`（policy gate + trust derivation）。(`docs/design/modules/agent/README.md`)
- [ ] Hooks 生命周期触发点与默认 hook 管理器。(`docs/design/modules/agent/README.md`)
- [ ] 对齐 EventLog / HITL 事件链（pause → wait → resume）。(`docs/design/modules/agent/README.md`)

## context
- [ ] 规范 `AssembledContext.metadata` 最小字段（context_id / tool_snapshot_hash）。(`docs/design/modules/context/README.md`)
- [ ] 定义 LTM/Knowledge 融合策略与预算归因。(`docs/design/modules/context/README.md`)
- [ ] 对齐工具快照记录与 EventLog 审计链。(`docs/design/modules/context/README.md`)

## tool
- [ ] 将 policy/hitl gate 接入 ToolLoop（与 `ISecurityBoundary` 结合）。(`docs/design/modules/tool/README.md`)
- [ ] 工具调用审计快照（capability hash / tool defs snapshot）。(`docs/design/modules/tool/README.md`)
- [ ] 能力等级与审批策略统一（risk_level ↔ approval policy）。(`docs/design/modules/tool/README.md`)
- [ ] 统一 tool defs schema（跨模型 adapter 一致性）。(`docs/design/modules/tool/README.md`)

## plan
- [ ] 将 ValidatedPlan.steps 绑定工具执行（计划驱动）。(`docs/design/modules/plan/README.md`)
- [ ] 计划 attempt 隔离（Context snapshot / rollback）。(`docs/design/modules/plan/README.md`)
- [ ] 统一证据模型（planner evidence ↔ tool evidence）。(`docs/design/modules/plan/README.md`)
- [ ] 明确 plan tool 的元数据与 policy gate 语义。(`docs/design/modules/plan/README.md`)

## model
- [ ] Prompt 不支持热更新；需重新构造 PromptStore（reload）。(`docs/design/modules/model/README.md`)
- [ ] 流式输出与增量 tool calls 支持。(`docs/design/modules/model/README.md`)
- [ ] 多模型策略（fallback/router/ensemble）。(`docs/design/modules/model/README.md`)
- [ ] Prompt 多阶段（plan/execute/verify）与上下文预算联动。(`docs/design/modules/model/README.md`)

## model / prompt
- [ ] PromptStore 热更新（reload / watcher）。(`docs/design/modules/model/Model_Prompt_Management.md`)
- [ ] 多阶段 prompt pack（plan/execute/verify）。(`docs/design/modules/model/Model_Prompt_Management.md`)
- [ ] 与上下文预算联动（压缩、摘要策略）。(`docs/design/modules/model/Model_Prompt_Management.md`)

## security
- [ ] 提供默认 Policy/Sandbox 实现。(`docs/design/modules/security/README.md`)
- [ ] 在 Agent 的 Plan→Execute 与 Tool invoke 前接入 policy gate。(`docs/design/modules/security/README.md`)
- [ ] 与 HITL (`IExecutionControl`) 形成审批闭环。(`docs/design/modules/security/README.md`)

## event
- [ ] 提供默认 EventLog 实现（持久化 + hash-chain）。(`docs/design/modules/event/README.md`)
- [ ] 统一 legacy event bus 与 WORM event log 的关系。(`docs/design/modules/event/README.md`)
- [ ] 定义稳定事件 taxonomy 与 payload schema。(`docs/design/modules/event/README.md`)

## hook
- [ ] 在 DareAgent 生命周期注入 hook 调用点。(`docs/design/modules/hook/README.md`)
- [ ] 明确 hook 的 payload schema 与错误处理策略。(`docs/design/modules/hook/README.md`)

## config
- [ ] 增加环境变量或多格式配置支持（YAML/TOML）。(`docs/design/modules/config/README.md`)
- [ ] enforce allowlists（allow_tools/allow_mcps）。(`docs/design/modules/config/README.md`)
- [ ] 配置热更新与订阅机制。(`docs/design/modules/config/README.md`)

## memory / knowledge
- [ ] 提供默认 LTM/Knowledge 实现（或接入外部向量库）。(`docs/design/modules/memory_knowledge/README.md`)
- [ ] 统一检索融合策略（排序、去重、预算控制）。(`docs/design/modules/memory_knowledge/README.md`)
- [ ] 知识作为 Tool 的统一策略（权限、计费、审计）。(`docs/design/modules/memory_knowledge/README.md`)
## skill
- [ ] 标准化“技能注入上下文”的默认路径与安全边界。(`docs/design/modules/skill/README.md`)
- [ ] skill 执行权限与审计机制。(`docs/design/modules/skill/README.md`)

## embedding
- [ ] 接入 Knowledge/RAG pipeline。(`docs/design/modules/embedding/README.md`)
- [ ] 统一配置与 adapter 选择策略。(`docs/design/modules/embedding/README.md`)
