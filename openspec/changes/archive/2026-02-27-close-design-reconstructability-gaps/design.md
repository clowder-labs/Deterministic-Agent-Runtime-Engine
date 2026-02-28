## Context

在完成 full review 与 security canonicalization 后，文档与实现的核心漂移已显著收敛；但“可重建性”仍存在三项阻塞缺口：

1. 缺少统一追踪矩阵（设计约束无法直接映射到实现与测试）。
2. plan/tool 审批语义存在分叉，文档未形成权威决策表。
3. 缺少“按文档重建”的操作型 SOP。

本变更用于把上述缺口转化为可执行治理资产，防止文档再次腐化。

## Goals / Non-Goals

### Goals

- 建立可重建性 P0/P1 缺口基线与 TODO 清单。
- 定义并落地重建治理规范（追踪矩阵 + 语义决策表 + 重建 SOP）。
- 将治理要求固化为 OpenSpec requirements，便于后续持续执行。

### Non-Goals

- 本变更不引入新的 runtime 业务能力。
- 本变更不重构现有 agent/tool 执行逻辑，只聚焦文档治理与可追踪性。

## Design Decisions

### 1) 治理对象分层

- **P0**：追踪矩阵、审批语义决策表、重建 SOP（阻塞可重建）。
- **P1**：状态标签标准化、漂移自动检测、周期性评审机制（长期防腐）。

### 2) 追踪矩阵作为单一入口

- 统一维护 `doc -> code -> tests -> status` 映射，避免信息散落在多个文档中。
- Architecture 负责给出矩阵入口，模块文档负责给出局部锚点。

### 3) 审批语义显式化

- 在 Architecture 中以决策表明确“当前语义 vs 目标语义 vs 迁移策略”，减少实现歧义。

## Risks and Mitigations

- 风险：新增治理文档增加维护成本。
  - 缓解：以单一矩阵入口集中维护，模块文档只保留必要锚点链接。
- 风险：治理要求落地慢，导致文档仍可能回退。
  - 缓解：用 OpenSpec tasks 分批推进，并在 project_overall_todos 追踪状态。

## Verification Plan

- `openspec validate close-design-reconstructability-gaps --type change --strict`
- 变更完整性检查：
  - gap 分析与 TODO 文件存在且可互相引用
  - proposal/spec/design/tasks 四件套完整
- 后续实施阶段再补：
  - 追踪矩阵完整性校验
  - 文档漂移检测脚本与 CI 校验
