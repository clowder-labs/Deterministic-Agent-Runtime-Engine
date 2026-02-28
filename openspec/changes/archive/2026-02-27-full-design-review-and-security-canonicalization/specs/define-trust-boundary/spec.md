## ADDED Requirements

### Requirement: DefaultSecurityBoundary 必须保持单一 canonical 导出路径

默认安全边界实现 MUST 仅通过 canonical facade `dare_framework.security` 暴露，禁止并行保留 legacy compatibility shim 导出路径。

#### Scenario: 运行时导入使用 canonical facade

- **WHEN** 运行时或测试代码需要默认安全边界
- **THEN** 导入路径为 `from dare_framework.security import DefaultSecurityBoundary`
- **AND** 运行时行为与导入路径无歧义

#### Scenario: 兼容 shim 路径被移除

- **WHEN** 维护者检查 `dare_framework/security/` 包结构
- **THEN** 不存在 `security/impl/default_security_boundary.py` 的兼容导出文件
- **AND** 文档不再宣称该兼容路径为受支持 API
