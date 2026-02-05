# Design TODO Index

> Status: generated from module docs (2026-02-05).
>
> 用途：集中查看当前架构/模块设计文档中的 TODO，便于分工与追踪。

## agent
- [ ] 将 ValidatedPlan.steps 驱动 Execute Loop（计划执行一致性）。(`docs/design/module_design/agent/README.md`)
- [ ] 引入 plan attempt snapshot/rollback，实现失败计划隔离。(`docs/design/module_design/agent/README.md`)
- [ ] 接入 `ISecurityBoundary`（policy gate + trust derivation）。(`docs/design/module_design/agent/README.md`)
- [ ] Hooks 生命周期触发点与默认 hook 管理器。(`docs/design/module_design/agent/README.md`)
- [ ] 对齐 EventLog / HITL 事件链（pause → wait → resume）。(`docs/design/module_design/agent/README.md`)

## context
- [ ] 为 `assemble()` 定义标准化 options（`query/top_k/budget_alloc/compression_hint`）。(`docs/design/module_design/context/README.md`)
- [ ] 规范 `AssembledContext.metadata` 审计字段与哈希计算口径。(`docs/design/module_design/context/README.md`)
- [ ] 在默认 Agent 调用链接入“预算检查 -> 压缩 -> 组装”的统一顺序。(`docs/design/module_design/context/README.md`)
- [ ] 明确 LTM 与 Knowledge 的冲突消解与证据优先级规则。(`docs/design/module_design/context/README.md`)
- [ ] 统一 `get(**kwargs)` 的可选参数协议（`top_k/min_similarity/filters`）。(`docs/design/module_design/context/README.md`)
- [ ] 给 LTM/Knowledge 定义统一去重 key 与冲突消解规则。(`docs/design/module_design/context/README.md`)
- [ ] 明确知识写入的权限、审计与成本计量策略（tool 与非 tool 路径一致性）。(`docs/design/module_design/context/README.md`)
- [ ] 增加“召回质量 + 压缩损失”观测指标，支持线下评估。(`docs/design/module_design/context/README.md`)

## tool
- [ ] 将 policy/hitl gate 接入 ToolLoop（与 `ISecurityBoundary` 结合）。(`docs/design/module_design/tool/README.md`)
- [ ] 工具调用审计快照（capability hash / tool defs snapshot）。(`docs/design/module_design/tool/README.md`)
- [ ] 能力等级与审批策略统一（risk_level ↔ approval policy）。(`docs/design/module_design/tool/README.md`)
- [ ] 统一 tool defs schema（跨模型 adapter 一致性）。(`docs/design/module_design/tool/README.md`)

## plan
- [ ] 将 ValidatedPlan.steps 绑定工具执行（计划驱动）。(`docs/design/module_design/plan/README.md`)
- [ ] 计划 attempt 隔离（Context snapshot / rollback）。(`docs/design/module_design/plan/README.md`)
- [ ] 统一证据模型（planner evidence ↔ tool evidence）。(`docs/design/module_design/plan/README.md`)
- [ ] 明确 plan tool 的元数据与 policy gate 语义。(`docs/design/module_design/plan/README.md`)

## model
- [ ] Prompt 不支持热更新；需重新构造 PromptStore（reload）。(`docs/design/module_design/model/README.md`)
- [ ] 流式输出与增量 tool calls 支持。(`docs/design/module_design/model/README.md`)
- [ ] 多模型策略（fallback/router/ensemble）。(`docs/design/module_design/model/README.md`)
- [ ] Prompt 多阶段（plan/execute/verify）与上下文预算联动。(`docs/design/module_design/model/README.md`)

## model / prompt
- [ ] PromptStore 热更新（reload / watcher）。(`docs/design/module_design/model/Model_Prompt_Management.md`)
- [ ] 多阶段 prompt pack（plan/execute/verify）。(`docs/design/module_design/model/Model_Prompt_Management.md`)
- [ ] 与上下文预算联动（压缩、摘要策略）。(`docs/design/module_design/model/Model_Prompt_Management.md`)

## security
- [ ] 提供默认 Policy/Sandbox 实现。(`docs/design/module_design/security/README.md`)
- [ ] 在 Agent 的 Plan→Execute 与 Tool invoke 前接入 policy gate。(`docs/design/module_design/security/README.md`)
- [ ] 与 HITL (`IExecutionControl`) 形成审批闭环。(`docs/design/module_design/security/README.md`)

## event
- [ ] 提供默认 EventLog 实现（持久化 + hash-chain）。(`docs/design/module_design/event/README.md`)
- [ ] 统一 legacy event bus 与 WORM event log 的关系。(`docs/design/module_design/event/README.md`)
- [ ] 定义稳定事件 taxonomy 与 payload schema。(`docs/design/module_design/event/README.md`)

## hook
- [ ] 在 DareAgent 生命周期注入 hook 调用点。(`docs/design/module_design/hook/README.md`)
- [ ] 明确 hook 的 payload schema 与错误处理策略。(`docs/design/module_design/hook/README.md`)

## config
- [ ] 增加环境变量或多格式配置支持（YAML/TOML）。(`docs/design/module_design/config/README.md`)
- [ ] enforce allowlists（allowtools/allowmcps）。(`docs/design/module_design/config/README.md`)
- [ ] 配置热更新与订阅机制。(`docs/design/module_design/config/README.md`)

## skill
- [ ] 标准化“技能注入上下文”的默认路径与安全边界。(`docs/design/module_design/skill/README.md`)
- [ ] skill 执行权限与审计机制。(`docs/design/module_design/skill/README.md`)

## embedding
- [ ] 接入 Knowledge/RAG pipeline。(`docs/design/module_design/embedding/README.md`)
- [ ] 统一配置与 adapter 选择策略。(`docs/design/module_design/embedding/README.md`)
