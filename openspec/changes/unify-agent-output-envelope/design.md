## Context

当前 runtime 结果类型在 agent 维度缺乏统一约束：`SimpleChatAgent`/`ReactAgent` 常返回字符串，`DareAgent` 可能返回结构化对象或字符串。虽然 `output_text` 有归一化能力，但 `output` 本体缺乏稳定 contract，导致 client/transport/测试需要处理多种分支。  
根据 `docs/design/modules/agent/TODO.md` 的 A-103，目标是统一为 output envelope，使得即使底层执行模式不同，外部观测面一致。

## Goals / Non-Goals

**Goals:**
- 为三类 agent 的 `RunResult.output` 提供统一 envelope：`content/metadata/usage`。
- 保持 `output_text == output.content` 的一致性规则。
- 在不引入新依赖的前提下完成变更并补齐契约测试。
- 更新文档与 OpenSpec 任务，形成可追溯证据。

**Non-Goals:**
- 不修改 ToolResult、PlanResult 等其他 domain 类型。
- 不扩展新的 transport 消息类型。
- 不在本变更中重做五层循环或 step-driven 逻辑。

## Decisions

### Decision 1: 在 agent 返回边界统一 envelope，而非在 `RunResult` dataclass 层强制
- 方案 A（采用）：在各 agent `execute(...)` 返回前构造 envelope，`RunResult` 继续保持通用 `Any` 类型。
- 方案 B（不采用）：直接收紧 `RunResult.output` 类型为专有 dataclass/TypedDict。
- 理由：A 变更面更小，不影响所有 `RunResult` 生产方；先统一主路径 agent 再逐步收敛类型系统。

### Decision 2: `content` 一律序列化为文本
- 方案 A（采用）：`content` 始终为 `str`，复用 `normalize_run_output(...)` 做文本提取与兜底。
- 方案 B（不采用）：`content` 允许 `str | dict | list`。
- 理由：A 与 A-103 目标一致，调用侧解析成本最低。

### Decision 3: `usage` 优先取模型 usage，缺失则为 `None`
- 对 `SimpleChatAgent` 直接使用单次 `response.usage`。
- 对 `ReactAgent`/`DareAgent` 在当前能力边界内先返回 `None` 或已有聚合值，不引入额外采集逻辑。

## Risks / Trade-offs

- [Risk] 现有依赖 `result.output` 为字符串的调用方可能断言失败  
  → Mitigation: 保持 `output_text` 不变并补齐回归测试；变更说明标记 BREAKING。

- [Risk] 对 `DareAgent` 的复杂输出进行文本化会丢失部分结构细节  
  → Mitigation: 通过 `metadata` 保留必要附加信息，`content` 只承担统一展示契约。

- [Risk] 不同 agent 的 usage 字段完整性不一致  
  → Mitigation: 明确 `usage` 可空，后续再独立补齐 usage 聚合。

## Migration Plan

1. 新增输出 envelope 构造 helper（复用 output normalizer）。
2. 为 `Simple/React/Dare` 接入统一 envelope 构造。
3. 先写/改失败测试验证 envelope 契约（RED），再实现（GREEN）。
4. 跑受影响单测与编译检查，修复回归。
5. 更新 `docs/design/modules/agent/TODO.md` 与 `docs/design/TODO_INDEX.md` 中 A-103 状态。

回滚策略：若出现不可接受兼容问题，回退 envelope 注入点到各 agent 原始返回逻辑并保留测试分支供后续迭代。

## Open Questions

- `DareAgent` 的 `usage` 是否应统一使用 session 级 token 聚合并写入 envelope（本次先可空）？
- 是否在下一轮将 envelope 提升为显式类型（TypedDict/dataclass）并在 `RunResult` 上收紧类型注解？
