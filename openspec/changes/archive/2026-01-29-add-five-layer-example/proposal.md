# Change: Add Five-Layer Coding Agent Example

## Why

当前 `examples/coding-agent` 依赖已归档的框架版本（`archive/frameworks/dare_framework/`），无法直接展示 `dare_framework` 的五层循环架构。需要创建一个新的示例分支，使用 `FiveLayerAgent` 实现完整的 Session → Milestone → Plan → Execute → Tool 循环编排，用于：

1. **验证五层循环架构** - 展示完整的循环编排实现
2. **提供学习参考** - 为开发者展示如何使用 `FiveLayerAgent`
3. **架构对齐验证** - 验证设计文档中的五层循环与实际实现的一致性
4. **支持迭代开发** - 为后续的系统提示词、HITL、安全边界等功能提供集成测试平台

## What Changes

- 在 `examples/` 下新建 `five-layer-coding-agent/` 目录
- 实现基于 `FiveLayerAgent` 的 coding agent 示例
- 提供完整的工具集（read_file, write_file, search_code, run_tests 等）
- 实现确定性 Planner 和 OpenAI Planner 两种模式
- 提供清晰的 README 文档和运行指南
- 包含单元测试和集成测试

这是一个**新增功能**，不影响现有代码。

## Impact

- **Affected specs**: `example-agent`（新增五层循环示例需求）
- **Affected code**:
  - `examples/` - 新增 `five-layer-coding-agent/` 目录
  - 无现有代码修改
- **Dependencies**: 需要 `dare_framework` 中的 `FiveLayerAgent` 已实现（当前状态：✅ 已实现）
- **Documentation**: 需要更新项目 README，添加新示例说明

## Risks

1. **实现依赖** - ✅ `FiveLayerAgent` 已实现（`dare_framework/agent/_internal/five_layer.py`）
2. **设计差距** - 根据 `gap_tracking.md`，系统提示词、`ISecurityBoundary`、`IExtensionPoint` 未完成，示例可能需要 mock 这些组件
3. **文档同步** - 需要与五层循环设计文档保持一致

## Alternatives Considered

1. **直接修改现有 coding-agent 示例** - 拒绝，因为会破坏归档示例的历史参考价值
2. **等待 FiveLayerAgent 完全成熟后再创建示例** - 拒绝，示例开发可以帮助发现设计问题，应该并行开发
3. **创建简化版示例** - 考虑，但完整示例更有价值，可以作为 Phase 1 先实现简化版
