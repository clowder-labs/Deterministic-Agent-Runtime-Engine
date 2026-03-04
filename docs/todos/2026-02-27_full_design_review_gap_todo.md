---
change_ids: []
doc_kind: todo
topics: ["design-review", "todo", "architecture"]
created: 2026-02-27
updated: 2026-03-04
status: active
---

# 2026-02-27 全量设计文档 Review：TODO 清单（第二轮刷新）

> 来源：`docs/todos/2026-02-27_full_design_review_gap_analysis.md`  
> 说明：所有项必须映射 Gap ID，并附可定位证据。

## 认领声明（Claim Ledger）

> 当前状态：本清单条目均为 `done`，暂无 `planned/active` 认领。  
> 若未来新增条目，需先登记 Claim 后再进入 `doing`。

| Claim ID | TODO Scope | Owner | Status | Declared At | Expires At | OpenSpec Change | Notes |
|---|---|---|---|---|---|---|---|
| N/A | N/A | N/A | released | 2026-03-02 | 2026-03-02 | N/A | 当前无活跃认领。 |

| ID | Priority | Status | Gap ID | Task | Owner | Evidence | Last Updated |
|---|---|---|---|---|---|---|---|
| FR-001 | P0 | done | FR-GAP-001 | 修正 `Architecture.md` 过时运行态断言（step-driven/security）。 | codex | `docs/design/Architecture.md`；`dare_framework/agent/dare_agent.py` | 2026-02-27 |
| FR-002 | P0 | done | FR-GAP-002 | 修正 `tool/README.md` 中 security gate 接入状态与 TODO。 | codex | `docs/design/modules/tool/README.md`；`dare_framework/agent/dare_agent.py` | 2026-02-27 |
| FR-003 | P0 | done | FR-GAP-003 | 修正 `plan/README.md` 的 step-driven 状态，回写真实限制。 | codex | `docs/design/modules/plan/README.md`；`dare_framework/agent/_internal/step_executor.py` | 2026-02-27 |
| FR-004 | P0 | done | FR-GAP-004 | 收敛 `DefaultSecurityBoundary` 为 canonical-only，移除 compatibility shim。 | codex | `dare_framework/security/__init__.py`；`tests/unit/test_kernel_flow.py`；`tests/unit/test_runtime_state.py` | 2026-02-27 |
| FR-005 | P1 | done | FR-GAP-005 | 修正 agent 详细设计与 TODO 状态（A-102）。 | codex | `docs/design/modules/agent/DareAgent_Detailed.md`；`docs/design/modules/agent/TODO.md` | 2026-02-27 |
| FR-006 | P0 | done | FR-GAP-006 | 修正 `DARE_Formal_Design.md` 的过时限制断言。 | codex | `docs/design/DARE_Formal_Design.md`；`dare_framework/agent/dare_agent.py`；`dare_framework/context/context.py`；`dare_framework/event/_internal/sqlite_event_log.py` | 2026-02-27 |
| FR-007 | P1 | done | FR-GAP-007 | 刷新 `TODO_INDEX.md`，移除已完成项并回写最新待办。 | codex | `docs/design/TODO_INDEX.md`；`docs/design/modules/*/README.md` | 2026-02-27 |
| FR-008 | P1 | done | FR-GAP-007 | 固化周期性全量设计 review 机制（节奏、责任、归档标准）。 | codex | `docs/guides/Documentation_First_Development_SOP.md`（Section 6）；`docs/todos/README.md` | 2026-02-27 |
| FR-009 | P1 | done | FR-GAP-008 | 为 14 个模块 README 补充测试锚点（或缺失声明 + 补测链接），闭合可重建验证链。 | codex | `docs/design/modules/*/README.md`（`### 测试锚点（Test Anchor）`）；`docs/design/modules/memory_knowledge/README.md`（缺失声明） | 2026-02-27 |
| FR-010 | P1 | done | FR-GAP-010 | 修复 active 设计文档中的失效代码路径锚点（context/tool）。 | codex | `docs/design/Architecture.md`；`docs/design/DARE_Formal_Design.md`；`docs/design/modules/context/README.md`；`docs/design/modules/tool/README.md` | 2026-02-27 |
| FR-011 | P2 | done | FR-GAP-009 | 补 embedding 域最小单测并回写模块文档测试锚点。 | codex | `tests/unit/test_embedding_openai_adapter.py`；`docs/design/modules/embedding/README.md`；`.venv/bin/python -m pytest -q tests/unit/test_embedding_openai_adapter.py` | 2026-02-27 |
| FR-012 | P2 | done | FR-GAP-011 | 补 `memory/knowledge` 域直连单测并替换当前“组合链路锚点”过渡声明。 | codex | `tests/unit/test_memory_knowledge_direct.py`；`docs/design/modules/memory_knowledge/README.md`；`.venv/bin/python -m pytest -q tests/unit/test_memory_knowledge_direct.py` | 2026-02-27 |

---

## 执行说明（SOP 对齐）

1. 本轮已完成 active 文档失效锚点修复，且核心设计与实现主链保持一致。
2. 当前剩余事项集中在“域直连测试资产补齐”层，不再是“核心运行态断言漂移”。
