## Why

`docs/design/modules/**/README.md` 中多份文档虽覆盖了流程/接口/字段，但未显式提供“总体架构”“异常与错误处理”章节，未满足 `docs/design/Design_Doc_Minimum_Standard.md` 的硬性要求。为保证“文档可重建实现”，需要统一补齐最小完备章节。

## What Changes

- 对 `docs/design/modules/*/README.md` 批量补充最小标准缺失章节，重点补齐：
  - 总体架构
  - 异常与错误处理
- 通过统一补充段落显式映射现有“核心流程/数据结构/关键接口”章节，确保每份模块文档都满足 5 类强制内容。
- 不修改运行时代码与接口行为，仅修正文档完备性。

## Capabilities

### New Capabilities
- `module-design-minimum-sections`: 规定模块设计文档必须显式包含最小完备标准的 5 类章节，并给出可定位实现证据。

### Modified Capabilities
- None.

## Impact

- Affected docs:
  - `docs/design/modules/*/README.md`
  - `docs/todos/archive/2026-02-27_design_code_gap_todo.md`（回写 DG-007 完成证据）
- No runtime behavior changes.
- No API or dependency changes.
