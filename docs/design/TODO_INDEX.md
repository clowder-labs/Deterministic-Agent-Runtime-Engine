# Design TODO Index

> Status: refreshed after full review (2026-02-27).
>
> 用途：集中查看当前架构/模块设计文档中的 TODO，便于分工与追踪。

## Current Sprint (Agent)
- [x] A-101 DareAgent 结构化拆分（`session/milestone/execute/tool` 内聚到 `dare_framework/agent/_internal/`，`dare_agent.py` 退化为门面编排）
- [x] A-102 step-driven 路径策略定稿（已实现最小闭环）
- [x] A-103 统一输出数据形状（`RunResult.output` envelope: `content/metadata/usage`）

## agent
- [ ] DareAgent 按 loop 职责拆分，降低单文件复杂度。(`docs/design/modules/agent/TODO.md`)
- [ ] 统一跨 agent 的 output 数据形状。(`docs/design/modules/agent/TODO.md`)
- [ ] 对齐 Plan 与 Tool 两个入口的审批语义（包含 wait/resume 一致性）。(`docs/design/modules/agent/DareAgent_Detailed.md`)

## context
- [ ] 规范 `AssembledContext.metadata` 最小字段（context_id / tool_snapshot_hash）。(`docs/design/modules/context/README.md`)
- [ ] 定义 LTM/Knowledge 融合策略与预算归因。(`docs/design/modules/context/README.md`)
- [ ] 对齐工具快照记录与 EventLog 审计链。(`docs/design/modules/context/README.md`)

## tool
- [ ] 工具调用审计快照（capability hash / tool defs snapshot）。(`docs/design/modules/tool/README.md`)
- [ ] 能力等级与审批策略统一（risk_level ↔ approval policy）。(`docs/design/modules/tool/README.md`)
- [ ] 统一 tool defs schema（跨模型 adapter 一致性）。(`docs/design/modules/tool/README.md`)
- [ ] 统一 `APPROVE_REQUIRED` 在 plan/tool 两个入口的行为语义。(`docs/design/modules/tool/README.md`)

## plan
- [ ] 评估是否将 `DefaultPlanAttemptSandbox` 下沉到 plan domain 默认实现。(`docs/design/modules/plan/README.md`)
- [ ] 统一证据模型（planner/tool/verify）字段 taxonomy。(`docs/design/modules/plan/README.md`)
- [ ] 扩展 step-driven 路径端到端覆盖（多步依赖/回滚与补救组合）。(`docs/design/modules/plan/README.md`)

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
- [ ] 提供 production-grade Policy/Sandbox 实现。(`docs/design/modules/security/README.md`)
- [ ] 与 HITL (`IExecutionControl`) 形成审批闭环（含宿主控制面桥接）。(`docs/design/modules/security/README.md`)
- [ ] 统一 security 事件 taxonomy（deny/approve_required/allow）。(`docs/design/modules/security/README.md`)

## event
- [ ] 评估大规模场景下的存储后端升级路径（WORM/远端签名/分片归档）。(`docs/design/modules/event/README.md`)
- [ ] 统一 legacy events 与 event domain 的迁移策略。(`docs/design/modules/event/README.md`)
- [ ] 定义稳定事件 taxonomy 与 payload schema（含 host-orchestrated client envelope 映射）。(`docs/design/modules/event/README.md`)

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
