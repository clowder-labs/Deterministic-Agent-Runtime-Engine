## Why

第二轮 full review 结论显示：模块设计文档虽已具备结构完整性，但“测试锚点”覆盖不足（仅 1/15 模块显式可定位测试），导致可重建验证链仍不闭环。
同时 embedding 域缺少最小直接单测，导致该域文档难以提供真实测试证据。

## What Changes

- 为模块设计文档补齐测试锚点规范并在本轮文档中落地。
- 为 embedding 域增加最小基线测试（适配器契约与回退行为）。
- 回写 full review gap/TODO 与 project overall TODO 状态，形成治理闭环。

## Capabilities

### New Capabilities
- `embedding-domain-baseline-validation`: 定义 embedding 域最小测试与文档测试锚点回写要求。

### Modified Capabilities
- `module-design-minimum-sections`: 强化模块文档“测试锚点”要求（显式锚点或缺失声明+补测追踪）。

## Impact

- 文档：`docs/design/modules/*/README.md`、`docs/todos/*`
- 测试：新增 `tests/unit/test_embedding_openai_adapter.py`
- 规范：本 change 对“文档可重建”的验证链路提出更严格约束
