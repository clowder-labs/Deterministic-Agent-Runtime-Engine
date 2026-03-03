## 1. Capability Discovery Bridge

- [x] 1.1 将 `actions:list` 暴露到 `run/script --headless --control-stdin` 的 host bridge。
- [x] 1.2 明确并验证 discovery 返回的是当前 CLI host protocol surface，而不是 unsolicited startup handshake。

## 2. Host Protocol Regression Coverage

- [x] 2.1 增加 `actions:list` 的宿主协议 happy path 集成测试。
- [x] 2.2 增加 capability discovery 与现有 approvals / MCP / skills / status 共存的回归测试。
- [x] 2.3 覆盖 discovery 相关 error branch 和“无 startup handshake”约束。

## 3. Docs And Evidence

- [x] 3.1 更新 `client/DESIGN.md` 与 `client/README.md`，锁定显式 discovery baseline 和 handshake 延后策略。
- [x] 3.2 回写 `docs/features/client-capability-discovery-and-host-tests.md`、master TODO 与 review/merge-gate evidence。
