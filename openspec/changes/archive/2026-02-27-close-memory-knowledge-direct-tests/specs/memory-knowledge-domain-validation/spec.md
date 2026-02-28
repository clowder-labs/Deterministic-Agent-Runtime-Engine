## ADDED Requirements

### Requirement: memory/knowledge 域必须具备直连测试基线

系统 MUST 为 `memory` 与 `knowledge` 域提供不依赖 Context 组合链路的直连单测，覆盖工厂构建与默认 rawdata 实现的核心契约。

#### Scenario: memory/knowledge 直连单测可验证核心契约
- **WHEN** 维护者执行 memory/knowledge 域直连单测
- **THEN** 可验证工厂配置解析、默认实现持久化/检索行为
- **AND** 测试不依赖外部网络服务

### Requirement: memory_knowledge 模块文档必须引用直连测试锚点

`docs/design/modules/memory_knowledge/README.md` MUST 在测试锚点段落引用 memory/knowledge 域直连测试路径；完成后不得继续保留“缺失直连单测”声明。

#### Scenario: 模块文档测试锚点不再依赖过渡声明
- **WHEN** 评审者检查 memory_knowledge 模块文档
- **THEN** 可定位到直连单测文件路径
- **AND** 文档中不存在“缺失直连单测”声明
