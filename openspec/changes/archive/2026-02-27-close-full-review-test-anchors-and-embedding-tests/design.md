## Context

当前仓库已完成可重建性治理 P0/P1 基线，但 full review 第二轮指出“文档 -> 代码 -> 测试”链路在模块维度仍不完整。
具体表现为：模块 README 大多缺少显式测试锚点；embedding 域尚无直接单测，无法给出稳定测试证据。

## Goals / Non-Goals

**Goals:**
- 为模块 README 增补可定位的测试锚点，支持从文档直达验证证据。
- 为 embedding 域补齐最小直接单测，覆盖关键适配器行为。
- 同步回写 full-review TODO 与项目总 TODO，维持治理台账一致性。

**Non-Goals:**
- 不改动 embedding 运行时行为。
- 不引入新的 runtime 能力或复杂策略框架。

## Decisions

1. 测试锚点采用“显式路径优先”策略：每个模块 README 增加 `测试锚点（Test Anchor）` 小节，至少给出一个测试文件路径。
2. 对尚无直连测试的模块，允许“缺失声明 + TODO 追踪”作为过渡，但必须提供当前可用的组合验证锚点。
3. embedding 域单测聚焦 `OpenAIEmbeddingAdapter` 的最小契约：
   - 缺依赖时报错语义
   - 单条/批量 embedding 返回结构
   - 空批量短路行为
   - endpoint + dummy key 构造语义

## Risks / Trade-offs

- [风险] 测试锚点可能随文件重命名失效。
  → Mitigation: 继续通过文档漂移检查与周期 review 更新锚点。
- [风险] embedding 单测依赖可选三方包语义，未来上游变化会影响测试稳定性。
  → Mitigation: 使用 monkeypatch/fake class，避免绑定外部网络与真实 SDK 行为。
