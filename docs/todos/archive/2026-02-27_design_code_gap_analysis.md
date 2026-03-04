---
change_ids: []
doc_kind: analysis
topics: ["design-code-gap", "analysis", "governance"]
created: 2026-02-27
updated: 2026-03-04
status: archived
---

# 设计文档与代码实现 Gap 分析（基线）

> 日期：2026-02-27  
> 范围：`docs/design/**` 与 `dare_framework/**` 的核心架构闭环（agent/plan/security/event/context/hook）  
> 目的：为后续 TODO 拆解与 OpenSpec 执行提供证据化输入。
> 状态：archived（2026-02-27，DG-001..DG-007 全部完成并归档）

## 1. 分析方法

- 以 `docs/design/Architecture.md`、`docs/design/modules/*/README.md` 为设计声明来源。
- 以 `dare_framework/**` 为实现证据来源。
- 按“设计声明 -> 代码证据 -> 影响 -> 建议动作”逐条评估。

## 2. Gap 清单

| Gap ID | 设计声明（Design Claim） | 代码证据（Code Evidence） | 影响评估 | 建议动作 | 优先级 |
|---|---|---|---|---|---|
| GAP-001 | 架构图声明 `Hooks (未接入)`、`Plan attempt isolation` 尚未实现。 | `docs/design/Architecture.md:118`, `docs/design/Architecture.md:273`；但 `dare_framework/agent/dare_agent.py:480-535` 已接入 snapshot/rollback，`dare_framework/agent/dare_agent.py:199` 已接入 `HookExtensionPoint`。 | 设计文档与实现事实不一致，导致评审和新开发者误判。 | 同步修订架构文档中的过时描述，保持“文档即事实”。 | P1 |
| GAP-002 | plan 模块目标包含 step-driven 执行。 | `docs/design/modules/plan/README.md:65-71`；`dare_framework/agent/dare_agent.py:134-185` 有 `execution_mode/step_executor` 字段，但 `_run_execute_loop` 仅 model-driven（`dare_framework/agent/dare_agent.py:673-760`），且 `ValidatedPlan.steps` 在无 validator 分支直接置空（`dare_framework/agent/dare_agent.py:617-621`）。 | 计划驱动执行未形成闭环，`ValidatedPlan.steps` 价值受限。 | 实现 step-driven 分支与 builder 装配，补回归测试。 | P0 |
| GAP-003 | security 模块要求 plan/tool 入口接入 policy gate。 | `docs/design/modules/security/README.md:58-71`；`dare_framework/security/kernel.py:16-44` 仅协议；`dare_framework/agent/dare_agent.py` 构造与执行路径未注入 `ISecurityBoundary`。 | 安全边界未落地，策略约束无法强制执行。 | 增加默认安全边界实现并接入 DareAgent 的 plan/tool 路径。 | P0 |
| GAP-004 | event 模块要求 WORM 审计日志具备默认实现。 | `docs/design/modules/event/README.md:57-64`；`dare_framework/event/` 当前仅 `kernel.py` 与 `types.py`，无默认持久化实现；`dare_framework/observability/_internal/event_trace_bridge.py` 仅包装已有 event log。 | 审计/replay 无默认可用闭环，部署落地成本高。 | 增加默认 EventLog 实现（最小可用 sqlite/hash-chain）。 | P0 |
| GAP-005 | context 设计目标包含 STM/LTM/Knowledge 融合。 | `docs/design/Architecture.md:338`；`dare_framework/context/context.py:186-201` 的默认 assemble 仅使用 `stm_get()` 与 `list_tools()`。 | 上下文工程能力与设计目标不一致，影响多轮任务质量。 | 实现默认融合策略或提供可配置 assemble 策略。 | P1 |
| GAP-006 | 设计文档应可重建实现，关键章节应完整。 | 模块文档扫描显示多个 README 缺少显式“总体架构”或“异常错误处理”章节（例如 `docs/design/modules/config/README.md`、`context/README.md`、`embedding/README.md`、`model/README.md`）。 | 文档可执行性不足，影响“代码缺失时可重建”的目标。 | 按统一标准补齐章节，并建立审查门禁。 | P1 |

## 3. 结论

- 当前最高优先级（P0）为：`step-driven 执行闭环`、`security boundary 落地`、`EventLog 默认实现`。
- 文档侧最高优先级（P1）为：`Architecture 过时叙述修订` 与 `模块文档最小完备化`。
- 本轮已先落地治理约束（SOP + 标准 + 导航），实现侧修复需进入 OpenSpec 逐项执行。

## 4. 输出与衔接

- 基于本分析生成 TODO：`docs/todos/archive/2026-02-27_design_code_gap_todo.md`
- 后续执行要求：每条 TODO 必须映射到 OpenSpec task，并回写证据与状态。
