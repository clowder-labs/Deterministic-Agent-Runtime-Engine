## Context

`dare_framework/agent/dare_agent.py` 当前集中承载五层编排的大部分控制流（milestone、execute、tool 等），并混合了事件记录、hook 调用、安全/审批门控、预算控制和错误归一化。该实现虽功能完整，但单文件复杂度高，导致两个问题：
1) 需求变更时难以局部演进；
2) 核心循环行为难以做小粒度单测，只能依赖大集成路径。

A-101 目标是在不改变外部行为和公共 API 的前提下，把循环职责拆到 agent 内部模块，形成稳定的“组装层 + 执行层”边界。

## Goals / Non-Goals

**Goals:**
- 将 `DareAgent` 内部编排拆分为独立内部组件（session/milestone/execute/tool）。
- 保持 `DareAgent` 对外 API、输入输出语义、事件/hook/安全门控行为一致。
- 为拆分后的执行层增加独立单测，覆盖关键成功/失败路径。
- 让 `dare_agent.py` 主要承担依赖组装和顶层状态转移。

**Non-Goals:**
- 不改变 `RunResult` 输出数据形状（A-103 单独处理）。
- 不引入新的公共接口或 breaking API。
- 不改变现有 security/approval/policy 语义，仅迁移位置并保证行为等价。

## Decisions

### Decision 1: 采用“薄门面 + 内部执行模块”而非一次性重写
- 方案 A（采用）：保留 `DareAgent` 作为门面，把循环逻辑逐步抽取到 `_internal` 模块，先保证行为等价。
- 方案 B（放弃）：直接重写为全新 orchestrator 框架并替换全部调用路径。
- 理由：A 风险可控、回归面可管理，适合单项单 PR 的节奏；B 变更面过大，不利于快速验证。

### Decision 2: 先按执行职责拆分，再处理跨模块复用
- 先拆分四个内部职责模块：
  - `session_orchestrator`
  - `milestone_orchestrator`
  - `execute_engine`
  - `tool_executor`
- 每个模块通过显式参数接收依赖（context/log/hook/security），避免隐式共享状态。
- 理由：先建立清晰边界，再讨论后续抽象可复用组件。

### Decision 3: 用行为回归测试锁住“等价性”
- 在保留现有测试的基础上，补充面向拆分模块的定向单测：
  - execute loop 分支（model-driven/step-driven）
  - tool loop 安全/审批/重试语义
  - milestone 失败路径的事件与 hook 完整性
- 理由：A-101 的核心验收是“结构变了，行为不变”。

## Risks / Trade-offs

- [风险] 抽取过程中参数传递遗漏，导致 hook/event payload 细节漂移
  → Mitigation: 先复制行为，再删除旧路径；对 payload 关键字段加断言测试。

- [风险] `_internal` 模块边界初版不完美，短期内仍有少量耦合
  → Mitigation: 本轮只追求最小可落地拆分；后续迭代优化边界。

- [风险] 拆分后可读性短期下降（调用栈变深）
  → Mitigation: 在 `DareAgent` 顶层保留清晰的编排入口注释和模块职责说明。

## Migration Plan

1. 新增 `_internal` 执行模块骨架与最小接口。
2. 按顺序迁移：tool -> execute -> milestone -> session 调用逻辑。
3. 每迁移一层即补/跑对应单测，确保行为不变。
4. 更新文档 TODO 状态与证据，完成 OpenSpec tasks 勾选。
5. 若出现不可快速定位回归，按模块粒度回滚到上一步（小步提交）。

## Open Questions

- 本轮是否需要把 `_run_plan_loop` 也一并抽离到独立模块，还是保留在 `DareAgent`（建议：保留，避免范围扩张）。
- 拆分后是否立即引入统一内部上下文对象（建议：暂不引入，先显式参数传递）。
