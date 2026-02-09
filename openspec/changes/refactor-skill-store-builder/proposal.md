# Change: Refactor skill loading to SkillStoreBuilder + skill-tool toggle

## Why
当前 skill 相关链路存在并行实现与配置分叉：builder 仍依赖 `initial_skill_path/skill_mode/skill_paths`，skill tool 有重复实现，`assemble_context` 与运行期 skill 注入路径不统一。这导致行为不可预测，也增加了外部集成复杂度。

## What Changes
- 引入 `SkillStoreBuilder` 作为统一装配入口：
  - 支持 `SkillStoreBuilder.config(config)` 基于 `workspace_dir/user_dir` 自动构建文件系统 loader。
  - 支持叠加外部 skill loader。
  - 支持按 `skill_id` 禁用技能。
- 调整 skill tool 装配策略：
  - 新增 `_enable_skill_tool` 开关语义：开启时自动注册 `search_skill`，关闭时不注入。
  - 开启 skill tool 时，默认 assemble 过程忽略 `sys_skill`，仅使用运行期已加载完整 skill 集合。
- 统一 skill 搜索工具实现为单一 `SearchSkillTool`，输出完整 skill payload（id/name/content/scripts）。
- 移除 Config 顶层 skill 专用字段：`initial_skill_path`、`skill_mode`、`skill_paths`。
  - skill 文件系统默认扫描改为由 `workspace_dir/user_dir` 派生。
- builder/context 协作重构：
  - builder 支持注入 `ISkillStore`、额外 skill loaders、禁用 skill id。
  - context 提供运行期完整 skill 缓存接口，供 assemble_context 合并。

## Impact
- Affected specs: `interface-layer`, `component-management`, `configuration-management`.
- Affected code: `dare_framework/agent/builder.py`, `dare_framework/context/*`, `dare_framework/skill/*`, `dare_framework/config/types.py`, `dare_framework/a2a/server/agent_card.py`.
- Breaking changes:
  - Config 不再暴露 `initial_skill_path/skill_mode/skill_paths`。
  - 依赖这些字段的外部调用方需迁移到 `SkillStoreBuilder` 或 builder 新 API。
