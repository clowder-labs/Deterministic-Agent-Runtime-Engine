## 1. Headless Mode Entry

- [x] 1.1 为 `client run` / `client script` 增加显式 `--headless` 参数，并定义与 `--output` 的互斥规则。
- [x] 1.2 在 headless 模式下禁用 `dare>` / `approve>` 等交互提示，并保证审批无法内联处理时走结构化失败路径。

## 2. Event Envelope V1

- [x] 2.1 为 headless 输出实现独立的 versioned envelope v1，不复用 legacy `log/event/result` JSON 行结构。
- [x] 2.2 在 envelope 中输出稳定的关联字段与事件序列，覆盖至少 lifecycle、tool 和 approval pending 事件。

## 3. Verification And Evidence

- [x] 3.1 为 headless happy path、参数错误路径、approval error path 增加或更新测试。
- [x] 3.2 验证 legacy automation JSON 未被回归破坏，并回写 `docs/features/client-headless-event-envelope-v1.md` 的 Evidence 区块。
- [x] 3.3 在 master TODO、OpenSpec artifacts、feature evidence 三处同步 Slice B 的状态与验证结果。
