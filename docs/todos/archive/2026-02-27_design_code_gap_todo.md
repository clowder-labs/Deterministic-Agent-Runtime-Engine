# 设计-实现 Gap 修复 TODO（由 2026-02-27 分析生成）

> 来源分析：`docs/todos/archive/2026-02-27_design_code_gap_analysis.md`  
> 状态：archived  
> Last Updated：2026-02-27
> Archive Note：DG-001..DG-007 已全部完成，相关 OpenSpec changes 已归档。

## 1. 执行清单

| ID | Priority | Status | Related Gap | Task | Owner | Evidence | Last Updated |
|---|---|---|---|---|---|---|---|
| DG-001 | P1 | done | GAP-001 | 同步修订 `docs/design/Architecture.md` 中 hooks/sandbox 的过时叙述，保证与当前实现一致。 | codex | `docs/design/Architecture.md`（hooks/sandbox/control-plane 状态对齐）；OpenSpec: `openspec/changes/archive/2026-02-27-sync-architecture-hooks-sandbox-status/` | 2026-02-27 |
| DG-002 | P0 | done | GAP-002 | 在 `DareAgent` 中落地 `step_driven` 分支，实际消费 `ValidatedPlan.steps` 与 `IStepExecutor`。 | codex | `dare_framework/agent/dare_agent.py`（新增 `_run_step_driven_execute_loop` 与模式分支）；`tests/unit/test_dare_agent_step_driven_mode.py`（step-driven 执行与前置条件失败测试）；OpenSpec: `openspec/changes/archive/2026-02-27-add-step-driven-execute-loop/` | 2026-02-27 |
| DG-003 | P1 | done | GAP-002 | 在 builder 暴露 `execution_mode/step_executor` 装配入口，并补配置约束校验。 | codex | `dare_framework/agent/builder.py`（新增 `with_execution_mode`、`with_step_executor`）；`tests/unit/test_dare_agent_step_driven_mode.py`（builder 装配测试）；OpenSpec: `openspec/changes/archive/2026-02-27-add-step-driven-execute-loop/` | 2026-02-27 |
| DG-004 | P0 | done | GAP-003 | 提供默认 `ISecurityBoundary` 实现并在 plan/tool 入口接入 policy gate。 | codex | `dare_framework/security/_internal/default_security_boundary.py`（默认安全边界实现）；`dare_framework/security/impl/default_security_boundary.py`（兼容导出）；`dare_framework/agent/dare_agent.py`（plan/tool policy gate + trusted invoke + execute_safe）；`tests/unit/test_dare_agent_security_boundary.py`（deny/approve/trust-rewrite/plan-gate）；OpenSpec: `openspec/changes/archive/2026-02-27-add-security-boundary-policy-gate/` | 2026-02-27 |
| DG-005 | P0 | done | GAP-004 | 提供默认 `IEventLog` 持久化实现（最小 sqlite + hash-chain + replay + verify）。 | codex | `dare_framework/event/_internal/sqlite_event_log.py`（SQLite + hash-chain + replay/verify）；`dare_framework/event/__init__.py`、`dare_framework/event/impl/sqlite_event_log.py`（canonical/compat 导出）；`tests/unit/test_event_sqlite_event_log.py`（append/query/replay/verify/tamper/trace-bridge 回归）；OpenSpec: `openspec/changes/archive/2026-02-27-add-default-eventlog-sqlite-hashchain/` | 2026-02-27 |
| DG-006 | P1 | done | GAP-005 | 补齐默认 context assemble 的 STM/LTM/Knowledge 融合策略（含预算与降级语义）。 | codex | `dare_framework/context/context.py`（DefaultAssembledContext 融合+预算降级）；`tests/unit/test_context_implementation.py`（融合/query/降级/异常回归）；OpenSpec: `openspec/changes/archive/2026-02-27-add-context-default-fusion-budgeted-assemble/` | 2026-02-27 |
| DG-007 | P1 | done | GAP-006 | 按 `docs/design/Design_Doc_Minimum_Standard.md` 补齐模块设计文档缺失章节。 | codex | `docs/design/modules/*/README.md`（批量补齐“总体架构/异常与错误处理”最小标准章节）；OpenSpec: `openspec/changes/archive/2026-02-27-add-module-doc-minimum-required-sections/` | 2026-02-27 |

## 2. 执行要求（强制）

- 每条 TODO 必须先建 OpenSpec 任务再改代码。
- 每条 TODO 完成后必须回写 `Status/Evidence/Last Updated`。
- 状态流转：`todo -> doing -> done`；阻塞使用 `blocked` 并写明阻塞原因。
- 不允许“批量 done 且无证据”。

## 3. 建议执行顺序

1. DG-001（收敛 Architecture 剩余过时叙述）
2. DG-007（按最小标准补齐各模块设计文档章节）
