## 1. Control-Stdin Entry

- [x] 1.1 为 headless `run/script` 增加 `--control-stdin` 参数，并定义与 interactive / legacy 输入模式的兼容边界。
- [x] 1.2 建立 command/result/error frame 解析与响应逻辑，保证请求 `id` 相关联且错误结构化返回。

## 2. Action Bridging

- [x] 2.1 将 `approvals:list/poll/grant/deny/revoke` 暴露到外部 control plane。
- [x] 2.2 将 `mcp:list/reload/show-tool` 与 `skills:list` 暴露到外部 control plane，并显式排除 `mcp:unload`。
- [x] 2.3 提供 `status:get` 的结构化会话快照返回。

## 3. Verification And Evidence

- [x] 3.1 增加 `control-stdin` happy path、unknown action、handler failure、session edge case 的测试。
- [x] 3.2 验证 Slice B headless event envelope 未被控制面引入回归破坏，并回写 `docs/features/client-external-control-plane-v1.md` 的 Evidence 区块。
