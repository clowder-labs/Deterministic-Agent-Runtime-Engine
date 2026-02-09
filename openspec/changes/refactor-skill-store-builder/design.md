## Context
当前 skill 相关能力有三条路径并存：
1. builder 通过旧 config 字段（`skill_mode/skill_paths/initial_skill_path`）控制模式。
2. search skill tool 存在重复实现，返回 payload 形态不一致。
3. assemble_context 支持外部注入，但默认实现与运行期 skill 装载未收敛。

这使得 `_enable_skill_tool` 的行为边界不清晰，也导致动态 skill 注入在不同 agent 上表现不一致。

## Goals / Non-Goals
- Goals:
  - 用一个统一入口（`SkillStoreBuilder`）组装可用 skill 集合。
  - `_enable_skill_tool` 成为唯一的 builder 内部模式开关。
  - 默认 assemble 策略在 skill-tool 模式下忽略 `sys_skill`，改为消费运行期已加载完整 skill。
  - 去掉 Config 顶层 skill 专用字段，减少配置分叉。
- Non-Goals:
  - 不在本变更实现复杂语义检索或向量化 skill 召回。
  - 不在本变更引入新的 skill 持久化后端。

## Decisions
- Decision: `SkillStoreBuilder` 负责组合 loader 与过滤逻辑，`SkillStore` 只负责索引与查询。
  - Rationale: 保持 store 职责单一，构建策略集中在 builder。

- Decision: `FileSystemSkillLoader` 支持 `Config` 输入并基于 `workspace_dir/user_dir` 推导默认目录。
  - Rationale: 满足“系统配置驱动路径”的要求，同时避免再引入 skill 专用 config 字段。

- Decision: 统一 `SearchSkillTool` 输出完整 skill payload，不直接耦合具体 agent 实现。
  - Rationale: 让运行时可选择将 payload 写入 context 缓存或走自定义 assemble 策略。

- Decision: 默认 `assemble_context` 增加运行期 skill 缓存合并逻辑，并受 `ignore_sys_skill` 开关控制。
  - Rationale: 同时支持 2.1（动态加载）和 2.2（外部静态 sys_skill）场景。

## Risks / Trade-offs
- 移除 Config 顶层 skill 字段属于破坏性变更，现有 JSON 配置中的对应键将失效。
- 旧 `SearchSkillTool` 行为差异可能影响依赖旧 output schema 的调用方。

Mitigation:
- 在 proposal 与代码注释中明确迁移路径。
- 保持 `with_skill_tool(bool)` API 稳定，尽量减少调用方改动。

## Migration Plan
1. 新增 `SkillStoreBuilder` 与 config-based loader 路径解析。
2. builder 切换到 `SkillStoreBuilder` 装配 skill store。
3. context 默认 assemble 引入运行期 skill 缓存逻辑。
4. 删除 Config skill 专用字段并修复引用。
5. 补充测试并验证。

## Open Questions
- 默认技能目录是否固定为 `<workspace_dir>/.dare/skills` 与 `<user_dir>/.dare/skills`。
  - 本次先采用该约定；若后续需要可通过新增 loader 注入扩展。
