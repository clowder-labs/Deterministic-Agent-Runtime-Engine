## ADDED Requirements

### Requirement: 模块文档必须维护显式测试锚点或缺失声明

每个 `docs/design/modules/*/README.md` MUST 包含“测试锚点（Test Anchor）”段落。
若该模块暂无直接单测，MUST 明确缺失声明并链接对应补测 TODO 项。

#### Scenario: 模块文档可直接定位验证入口
- **WHEN** 评审者阅读任一模块 README
- **THEN** 能定位到至少一个测试文件路径
- **AND** 若无直接单测，文档明确给出缺失说明与补测追踪链接
