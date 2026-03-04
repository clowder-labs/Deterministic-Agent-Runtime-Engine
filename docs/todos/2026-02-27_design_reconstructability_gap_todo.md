---
change_ids: []
doc_kind: todo
topics: ["design-reconstructability", "todo", "governance"]
created: 2026-02-27
updated: 2026-03-04
status: active
---

# 2026-02-27 可重建性 Gap TODO（P0/P1）

> 来源：`docs/todos/2026-02-27_design_reconstructability_gap_analysis.md`  
> 执行模型：文档先行 -> OpenSpec change -> 实施 -> 回写证据 -> 归档

## 认领声明（Claim Ledger）

> 当前状态：本清单条目均为 `done`，暂无 `planned/active` 认领。  
> 若未来新增条目，需先登记 Claim 后再进入 `doing`。

| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| N/A | N/A | N/A | released | 2026-03-02 | 2026-03-02 | N/A | 当前无活跃认领。 |

| ID | Priority | Status | Gap ID | Task | Owner | Evidence | Last Updated |
|---|---|---|---|---|---|---|---|
| DR-001 | P0 | done | DR-GAP-001 | 建立全局追踪矩阵：每条关键设计约束映射 `doc -> code -> tests -> status`。 | codex | `docs/design/Design_Reconstructability_Traceability_Matrix.md`；`openspec/changes/archive/2026-02-27-close-design-reconstructability-gaps/` | 2026-02-27 |
| DR-002 | P0 | done | DR-GAP-002 | 编制审批语义决策表：明确 Plan/Tool 入口当前行为、目标行为与迁移策略。 | codex | `docs/design/Architecture.md`（审批语义决策表）；`openspec/changes/archive/2026-02-27-close-design-reconstructability-gaps/` | 2026-02-27 |
| DR-003 | P0 | done | DR-GAP-003 | 新增“按文档重建”SOP（重建顺序、最小验收测试、回滚与归档规范）。 | codex | `docs/guides/Design_Reconstruction_SOP.md`；`openspec/changes/archive/2026-02-27-close-design-reconstructability-gaps/` | 2026-02-27 |
| DR-004 | P1 | done | DR-GAP-004 | 统一模块文档 as-is/to-be 模板，强制 `landed/partial/planned` 状态标签。 | codex | `docs/design/modules/*/README.md`；`openspec/changes/archive/2026-02-27-close-design-reconstructability-gaps/` | 2026-02-27 |
| DR-005 | P1 | done | DR-GAP-005 | 增加文档漂移自动检测脚本并接入 CI。 | codex | `scripts/ci/check_design_doc_drift.sh`；`.github/workflows/ci-gate.yml`；`openspec/changes/archive/2026-02-27-close-design-reconstructability-gaps/` | 2026-02-27 |
| DR-006 | P1 | done | DR-GAP-006 | 将可重建性 P0/P1 清单固化到项目总 TODO，并定义周期性评审节奏。 | codex | `docs/todos/project_overall_todos.md`；`docs/guides/Documentation_First_Development_SOP.md`；`openspec/changes/archive/2026-02-27-close-design-reconstructability-gaps/` | 2026-02-27 |

---

## 与 OpenSpec 绑定

- 归档 change：`openspec/changes/archive/2026-02-27-close-design-reconstructability-gaps/`
- 已执行映射：
  - DR-001/002/003 -> P0 apply tasks（已完成）
  - DR-004/005/006 -> P1 apply tasks（已完成）
