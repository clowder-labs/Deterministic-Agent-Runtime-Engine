## Context

`DG-001` 的目标是消除 `docs/design/Architecture.md` 与当前代码实现之间的事实偏差。当前偏差集中在两个关键点：

1. Hook 接入状态：架构图仍写 `Hooks (未接入)`，但 `DareAgent` 已在生命周期关键阶段通过 `HookExtensionPoint` 触发 hooks。
2. Plan Attempt Isolation：文档仍写“未实现 snapshot/rollback”，但 `DareAgent` 已默认注入 `DefaultPlanAttemptSandbox`，并在 milestone attempt 中执行 snapshot / rollback / commit。

该偏差会影响后续设计评审、TODO 拆解优先级和新成员认知，因此需要以文档优先流程修正为“实现事实基线 + 明确剩余 TODO”。

## Goals / Non-Goals

**Goals:**
- 让 `docs/design/Architecture.md` 对 hooks 与 sandbox 的状态描述与代码实现一致。
- 明确“已落地基线能力”与“仍待完善项”的边界，避免用“未接入/未实现”覆盖已实现能力。
- 回写 TODO（DG-001）证据，使治理闭环完整。

**Non-Goals:**
- 不修改 `dare_framework/**` 运行时代码。
- 不引入新的 hooks payload schema 或新的 sandbox 范围（如 LTM/Knowledge snapshot）。
- 不调整 DG-007 的文档补全范围。

## Decisions

1. 仅修订陈旧断言，不扩大文档改写范围。
   - Rationale: DG-001 是“文档事实对齐”任务，范围过大会与 DG-007 交叉。
   - Alternative: 一次性全面重写 Architecture；代价高且风险大。

2. 使用“基线已落地 + 后续 TODO”表达状态。
   - Rationale: 能同时保留真实性和路线图，不会误导为“全部完成”。
   - Alternative: 仅改成“已完成”；会掩盖尚未完成的 payload 规范化、严格隔离扩展等工作。

3. 以代码证据点驱动文档更新。
   - Rationale: 满足“文档可重建实现”的目标，降低主观描述偏差。
   - Alternative: 口径化描述不绑定证据；后续容易再次漂移。

## Risks / Trade-offs

- [Risk] 仅改文本可能遗漏同页其它冲突句子 → Mitigation: 通过关键词扫描（未接入/snapshot/rollback）做二次校验。
- [Risk] 将“STM 隔离基线”误解为“全状态隔离” → Mitigation: 在文档中明确当前隔离范围是 STM snapshot 基线。
- [Risk] 多个并行变更同时修改 Architecture 导致冲突 → Mitigation: 在 DG-001 中尽量最小化改动块并记录证据点。

## Migration Plan

1. 更新 `docs/design/Architecture.md` 中 hooks/sandbox 的陈旧描述。
2. 校验 OpenSpec 变更完整性（strict validate）。
3. 回写 `docs/todos/archive/2026-02-27_design_code_gap_todo.md` 的 DG-001 状态与证据。
4. 完成后归档本变更。

## Open Questions

- 是否需要在 DG-007 中补充“Architecture 事实校验清单”作为持续门禁？（本变更不处理）
