## Context

本次变更不是单点 bug 修补，而是一次“防腐化”治理：以完整评审方式校准设计文档与实现，确保文档可作为重建依据。当前已识别两类关键偏差：

1. 核心文档存在过时断言（如 step-driven 与 security gate 状态）。
2. `DefaultSecurityBoundary` 同时存在 canonical 与 compatibility 导出，破坏单一路径。

## Goals / Non-Goals

### Goals

- 完整评审 Architecture + module docs，并修复与现状冲突的断言。
- 将默认安全边界收敛为单一路径导出。
- 形成完整 gap 分析、TODO、证据闭环。

### Non-Goals

- 本轮不引入新的安全策略引擎或 sandbox backend。
- 本轮不重写无关模块实现，仅做与本次评审结论直接相关的修订。

## Design Decisions

### 1) 文档完整评审优先于“最小补充”

- 评审范围覆盖 `docs/design/Architecture.md` 与 `docs/design/modules/*/README.md`。
- 每个模块输出 `aligned` / `drift` 状态结论。
- 对核心 drift（Architecture/plan/tool/security/agent）直接修订权威文档。

### 2) 安全边界 canonical-only

- `DefaultSecurityBoundary` 的公开路径仅保留 `dare_framework.security` facade。
- 移除 `dare_framework/security/impl/default_security_boundary.py` compatibility shim。
- 所有导入（含测试）统一迁移到 canonical 路径。

### 3) SOP 产物完整闭环

- 生成本轮 full review 的 gap 分析与 TODO 清单。
- TODO 项与 OpenSpec 任务一一映射，并在完成后回写证据。

## Risks and Mitigations

- 风险：移除 compatibility 路径可能影响遗留导入。
  - 缓解：仓内全量搜索并同步迁移所有导入；在变更说明中标记 BREAKING。
- 风险：文档修订面较大导致遗漏。
  - 缓解：以“核心域优先 + 全量评审清单”方式输出可核验证据。

## Verification Plan

- `openspec validate full-design-review-and-security-canonicalization --type change --strict`
- 针对性测试：
  - `pytest -q tests/unit/test_dare_agent_security_boundary.py`
  - `pytest -q tests/unit/test_dare_agent_step_driven_mode.py`
- 导入路径校验：
  - `rg -n "security\\.impl\\.default_security_boundary" dare_framework tests docs`
