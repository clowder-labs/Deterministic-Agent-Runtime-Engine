## ADDED Requirements

### Requirement: 模块文档必须维护实现锚点与测试锚点

每个 `docs/design/modules/*/README.md` MUST 提供至少一组实现锚点与测试锚点，支撑“文档可重建”验证。

#### Scenario: 模块能力可映射到代码与测试

- **WHEN** 评审者检查模块文档的关键能力段落
- **THEN** 可定位到至少一个实现文件与对应验证测试

### Requirement: 模块文档必须标记能力状态

每个模块文档 MUST 为关键能力标记状态（`landed` / `partial` / `planned`），禁止混用未来目标与当前事实。

#### Scenario: 模块文档状态语义清晰

- **WHEN** 评审者阅读模块文档
- **THEN** 能区分已落地能力与规划能力
- **AND** 不会把 planned 项误读为当前实现
