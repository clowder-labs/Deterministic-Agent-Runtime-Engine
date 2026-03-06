## 1. Session Snapshot Persistence

- [x] 1.1 为 `client/` 新增 workspace 级 session snapshot store，并定义最小 JSON schema。
- [x] 1.2 在 `chat/run/script` 执行后写回 snapshot，保证 `session_id`、mode 与 STM 历史可恢复。

## 2. Resume Command Surface

- [x] 2.1 为 `chat/run/script` 增加 `--resume [session-id|latest]`。
- [x] 2.2 恢复后复用原 `session_id`，并明确恢复边界为 history + mode，status 重置为 `idle`。

## 3. Tests And Docs

- [x] 3.1 增加 unit/integration 测试，覆盖 latest 选择、指定 session 恢复、resume 后继续执行、缺失 session 错误。
- [x] 3.2 更新 `client/DESIGN.md`、`client/README.md` 与 `docs/features/client-session-resume.md` 证据区。

## 4. Session Discovery

- [x] 4.1 增加 `dare sessions list` 与 `/sessions list` 命令面。
- [x] 4.2 返回按更新时间排序的 session 摘要，并补对应 unit/integration 测试与 README。

## 5. Integration Compatibility

- [x] 5.1 为 `chat/run/script` 增加 `--session-id` 兼容入口，并与 `--resume` 冲突行为做确定性参数校验。
- [x] 5.2 为 headless `--control-stdin` 增加 `session:resume` action，更新 `actions:list` 并补 unit/integration 与 README/DESIGN 覆盖。
