## Why

当前 `memory_knowledge` 模块文档虽然已有测试锚点段落，但仍依赖 Context 组合链路作为过渡验证；缺少 memory/knowledge 域的直连单测，影响该域问题定位与回归颗粒度。

## What Changes

- 为 memory/knowledge 域补最小直连单测（不依赖 Context 组合链路）。
- 回写 `docs/design/modules/memory_knowledge/README.md` 测试锚点，移除“缺失声明”过渡描述。
- 回写 full-review 与项目总 TODO，关闭 FR-012 / T6-5。

## Capabilities

### New Capabilities
- `memory-knowledge-domain-validation`: 定义 memory/knowledge 域直连测试基线与文档锚点回写要求。

### Modified Capabilities
- `module-design-minimum-sections`: 强化“测试锚点”在有直连测试资产时必须引用直连测试，避免长期依赖过渡声明。

## Impact

- 测试：`tests/unit/`（新增 memory/knowledge 直连测试）
- 文档：`docs/design/modules/memory_knowledge/README.md`、`docs/todos/*`
- specs：新增 memory/knowledge 域验证规范，更新模块文档最小标准
