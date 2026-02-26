# DARE Client CLI

统一对外 CLI 入口，面向 `dare_framework` 的任务执行与运行时控制。

## 运行方式

```bash
# 仓库根目录
.venv/bin/python -m client --help

# 可编辑安装后使用 console script
.venv/bin/pip install -e .
.venv/bin/dare --help
```

如果是在离线或受限网络环境，可跳过依赖安装，仅安装 CLI 入口：

```bash
.venv/bin/pip install -e . --no-deps
```

## 常用命令

```bash
# 交互模式
.venv/bin/python -m client chat

# 一次性执行
.venv/bin/python -m client run --task "读取 README 并总结"
# 一次性执行（审批等待超时，默认 120s）
.venv/bin/python -m client run --task "读取 README 并总结" --approval-timeout-seconds 120
# 一次性执行（自动审批指定工具，例如 run_command）
.venv/bin/python -m client run --task "读取 README 并总结" --auto-approve-tool run_command

# 脚本模式
.venv/bin/python -m client script --file /abs/path/to/demo.txt
# 仓库内示例脚本
.venv/bin/python -m client chat --script client/examples/basic.script.txt

# 审批控制
.venv/bin/python -m client approvals list
.venv/bin/python -m client approvals poll --timeout-ms 30000
.venv/bin/python -m client approvals grant <request_id> --scope workspace --matcher exact_params

# MCP 控制
.venv/bin/python -m client mcp list
.venv/bin/python -m client mcp inspect
.venv/bin/python -m client mcp reload

# 诊断（不要求模型可执行）
.venv/bin/python -m client doctor
```

## 配置

默认配置来源：

1. `--workspace` 指定目录下 `.dare/config.json`
2. `--user-dir` 指定目录下 `.dare/config.json`
3. CLI flags 覆盖（`--adapter/--model/--api-key/...`）

> 在受限环境中建议显式传入 `--user-dir`，避免写入不可访问的 home 目录。

## 输出与退出码

- `--output human`：人类可读日志（默认）
- `--output json`：结构化行输出，适合脚本集成

JSON 行结构（简化）：

- 日志：`{"type":"log","level":"info|warn|ok|error","message":"..."}`
- 事件：`{"type":"event","event":"header|mode|plan_preview|transport","data":{...}}`
- 结果：`{"type":"result","data":{...}}`

退出码约定：

- `0`：成功
- `1`：执行失败
- `2`：参数错误
- `3`：诊断或配置检查失败
- `130`：中断退出

说明：`script` 模式下只要任一任务失败，最终退出码为 `1`。

`run` 模式若触发工具审批并超过 `--approval-timeout-seconds`，会以失败退出，避免长时间无反馈阻塞。

`run` 模式可使用：
- `--auto-approve`：启用内置低风险工具自动审批名单。
- `--auto-approve-tool <name>`：追加指定工具到自动审批名单（可重复传入）。
