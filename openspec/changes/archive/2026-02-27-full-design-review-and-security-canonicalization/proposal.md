## Why

当前 `docs/design` 与实现之间已经出现多处“文档过时但代码已变化”的偏差，继续沿用最小补充策略会放大腐化风险并误导后续 agent 开发。与此同时，`DefaultSecurityBoundary` 存在双路径导出（canonical + compatibility shim），破坏了“单一权威实现面”的目标。

## What Changes

- 对 `docs/design` 执行完整评审（非最小补丁），覆盖 Architecture 与各 domain 设计文档，修复与当前实现冲突的状态描述。
- 明确并落地 `DefaultSecurityBoundary` 的单一路径策略：仅保留 canonical 导出，移除 compatibility 导出路径。**BREAKING**
- 产出本轮完整 gap 分析与 TODO 清单，并按文档先行 SOP 回写证据与状态。
- 同步 OpenSpec 与关键测试，确保文档、规格、实现一致。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `architecture-documentation-alignment`: 扩展为“完整评审”标准，不仅修补最小条目。
- `define-trust-boundary`: 明确默认安全边界的 canonical API 面，禁止兼容性双导出。
- `module-design-minimum-sections`: 在“最小章节”之外增加“全量评审与状态校准”的治理要求。

## Impact

- 文档：`docs/design/Architecture.md`、`docs/design/modules/*/README.md`（重点：plan/tool/security/agent）。
- 代码：`dare_framework/security/impl/*`、测试导入路径。
- 治理产物：`docs/todos/` 新增本轮 full review gap 分析与 TODO 文档。
