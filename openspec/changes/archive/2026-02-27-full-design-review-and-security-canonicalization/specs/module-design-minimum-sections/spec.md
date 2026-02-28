## ADDED Requirements

### Requirement: 最小章节标准之外必须包含状态校准

模块设计文档除了满足“总体架构/核心流程/数据结构/关键接口/异常处理”五类最小章节外，MUST 对关键能力给出 `landed` / `partial` / `planned` 的当前状态，避免“仅补章节、不校状态”。

#### Scenario: 模块文档可区分已落地与待落地能力

- **WHEN** 评审者查看任意模块 README
- **THEN** 能定位到关键能力状态标记（landed/partial/planned）
- **AND** 不会把已实现能力继续描述为“未实现”

### Requirement: 全量设计评审应周期性执行并回写结果

文档治理 MUST 支持周期性全量评审，并把结果写入 `docs/todos` 的 gap 分析与 TODO 清单，再映射到 OpenSpec change 执行。

#### Scenario: 全量评审流程闭环

- **WHEN** 发起一次全量设计评审
- **THEN** 先更新设计文档，再生成 gap 与 TODO，再推进 OpenSpec 修复
- **AND** 完成后回写 evidence 并归档评审产物
