## ADDED Requirements

### Requirement: embedding 域必须具备最小直接测试基线

系统 MUST 为 `OpenAIEmbeddingAdapter` 提供最小直接单测，覆盖缺依赖报错、单条/批量返回结构与空批量短路行为。

#### Scenario: embedding 关键契约可被自动化验证
- **WHEN** 维护者执行 embedding 域单测
- **THEN** 可以验证适配器核心行为与错误语义
- **AND** 测试不依赖外部网络调用

### Requirement: embedding 模块文档必须链接基线测试锚点

`docs/design/modules/embedding/README.md` MUST 回写 embedding 基线测试锚点，确保文档到验证路径可追溯。

#### Scenario: embedding 文档具备测试证据链接
- **WHEN** 评审者检查 embedding 模块文档
- **THEN** 能看到对应测试文件路径
