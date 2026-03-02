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
.venv/bin/python -m client approvals grant <request_id> --scope workspace --matcher exact_params [--session-id session-id]

# MCP 控制
.venv/bin/python -m client mcp list
.venv/bin/python -m client mcp inspect
.venv/bin/python -m client mcp reload

# 诊断（不要求模型可执行）
.venv/bin/python -m client doctor
```

## 配置

### 配置文件位置与覆盖顺序

默认会读取两个配置文件：

1. `--user-dir` 指定目录下 `.dare/config.json`
2. `--workspace` 指定目录下 `.dare/config.json`
3. CLI flags 最终覆盖（`--adapter/--model/--api-key/--endpoint/--max-tokens/...`）

也就是实际优先级是：`user < workspace < CLI flags`。

补充说明：

- 两个配置文件如果不存在，会自动创建为空对象 `{}`。
- 配置是深合并：字典会逐层合并；标量和数组会被高优先级配置整体覆盖。
- `--workspace` 默认为当前目录，`--user-dir` 默认为当前用户 home 目录。

> 在受限环境中建议显式传入 `--user-dir`，避免写入不可访问的 home 目录。

首次初始化时，也可以直接参考仓库内的示例文件：

- `/.dare/config.json.example`：OpenAI 最小配置
- `/.dare/config.openrouter.example.json`：OpenRouter 最小配置
- `/.dare/config.advanced.example.json`：带 `cli.log_path/endpoint/proxy/max_tokens` 的进阶配置

### 最小可用 LLM 配置

最常见的做法是在 `.dare/config.json` 里写一个 `llm` 段：

```json
{
  "llm": {
    "adapter": "openai",
    "model": "gpt-4o-mini",
    "api_key": "sk-..."
  }
}
```

如果你不想把密钥写进配置文件，也可以使用环境变量：

```bash
export OPENAI_API_KEY=sk-...
```

这时 `config.json` 可以只保留模型相关字段：

```json
{
  "llm": {
    "model": "gpt-4o-mini"
  }
}
```

如果你就在当前仓库里试用 CLI，最省事的起点是：

```bash
cp .dare/config.json.example .dare/config.json
export OPENAI_API_KEY=sk-...
```

如果你要试 OpenRouter，可以直接改用：

```bash
cp .dare/config.openrouter.example.json .dare/config.json
export OPENROUTER_API_KEY=sk-or-...
```

### `llm` 字段说明

- `adapter`：模型适配器，当前支持 `openai` 和 `openrouter`。不写时默认是 `openai`。
- `model`：模型名，例如 `gpt-4o-mini`、`gpt-4.1`、`qwen/qwen3-coder:free`。
- `api_key`：模型服务密钥。也可以通过环境变量提供。
- `endpoint`：自定义 OpenAI-compatible base URL。对 `openrouter` 来说会作为 `base_url` 使用。
- `proxy`：代理配置，支持 `http`、`https`、`no_proxy`、`use_system_proxy`、`disabled`。
- 其他未显式声明的字段会进入 `llm.extra`，并透传给 adapter；例如可以直接写 `temperature`、`max_tokens`。

### `cli` 字段说明

- `cli.log_path`：CLI 日志文件路径。
- 不配置时，默认写到当前工作目录下的 `./dare.log`。
- 如果配置的是相对路径，也按当前工作目录解析；例如 `logs/dare.log` 会落到当前目录下的 `logs/dare.log`。

示例：

```json
{
  "cli": {
    "log_path": "logs/dare.log"
  }
}
```

`proxy` 的优先级规则：

- `disabled: true` 时，显式关闭代理，并忽略其他代理字段。
- `use_system_proxy: true` 时，使用系统代理环境变量，并忽略显式 `http/https`。
- 否则使用配置中的 `https` 或 `http`。

### 常见 LLM 配置示例

OpenAI：

```json
{
  "llm": {
    "adapter": "openai",
    "model": "gpt-4o-mini"
  }
}
```

配合环境变量：

```bash
export OPENAI_API_KEY=sk-...
```

OpenRouter：

```json
{
  "llm": {
    "adapter": "openrouter",
    "model": "qwen/qwen3-coder:free"
  }
}
```

配合环境变量：

```bash
export OPENROUTER_API_KEY=sk-or-...
export OPENROUTER_MODEL=qwen/qwen3-coder:free
# 可选，默认就是 https://openrouter.ai/api/v1
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

OpenAI-compatible / 自建模型网关：

```json
{
  "llm": {
    "adapter": "openai",
    "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
    "endpoint": "http://127.0.0.1:8000/v1",
    "api_key": "dummy-key"
  }
}
```

如果服务不校验密钥，仍建议显式给一个占位值，例如 `dummy-key`，这样 `doctor` 检查不会报 missing API key。

仓库里也提供了对应的完整示例文件：

- `/.dare/config.json.example`
- `/.dare/config.openrouter.example.json`
- `/.dare/config.advanced.example.json`

对应内容如下，便于直接在 README 里参考：

`/.dare/config.openrouter.example.json`

```json
{
  "llm": {
    "adapter": "openrouter",
    "model": "qwen/qwen3-coder:free"
  }
}
```

`/.dare/config.advanced.example.json`

```json
{
  "cli": {
    "log_path": "logs/dare.log"
  },
  "llm": {
    "adapter": "openai",
    "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
    "endpoint": "http://127.0.0.1:8000/v1",
    "api_key": "dummy-key",
    "max_tokens": 4096,
    "temperature": 0.2,
    "proxy": {
      "https": "http://127.0.0.1:7890",
      "no_proxy": "127.0.0.1,localhost"
    }
  }
}
```

### 临时覆盖配置

临时切模型或切换 provider 时，可以直接用 CLI flags 覆盖文件配置：

```bash
.venv/bin/python -m client \
  --adapter openrouter \
  --model qwen/qwen3-coder:free \
  --api-key "$OPENROUTER_API_KEY" \
  chat
```

或者只临时改 endpoint：

```bash
.venv/bin/python -m client \
  --endpoint http://127.0.0.1:8000/v1 \
  run --task "读取 README 并总结"
```

### 如何确认配置是否生效

建议按下面顺序检查：

```bash
# 查看最终生效的合并配置
.venv/bin/python -m client config show

# 查看当前 runtime 选中的模型信息
.venv/bin/python -m client model show

# 做环境与依赖诊断
.venv/bin/python -m client doctor
```

这三个命令分别用于：

- `config show`：确认 `llm`、`mcp_paths`、`allow_tools` 等最终生效值。
- `model show`：确认 runtime 实际加载的 adapter 名称和 model 名称。
- `doctor`：检查配置文件是否存在、API key 是否可见、adapter 依赖是否安装、MCP 路径是否有效。

### LLM 相关依赖

如果你是用 `pip install -e . --no-deps` 只安装 CLI 入口，还需要自行安装模型适配器依赖：

- `openai` adapter：需要 `langchain-openai`
- `openrouter` adapter：需要 `openai`

否则 `doctor` 会提示 adapter probe 或依赖缺失，runtime 也无法正常启动。

## 输出与退出码

- `--output human`：终端只显示用户交互内容；CLI 日志写入 `cli.log_path` 指定文件，默认 `./dare.log`
- `--output json`：结构化行输出，适合脚本集成

`human` 模式下常见行为：

- 启动信息、运行时状态、自动审批等日志不再打印到终端，会进入日志文件。
- 任务结果、plan preview、显式命令输出、需要用户处理的错误/审批提示仍会显示在终端。
- `chat` 模式下，发送消息后如果任务还没完成，CLI 不会立刻再次显示 `dare>` 提示；等回复完成后才会回到下一次输入。
- `chat` + `human` 模式下，如果运行过程中出现工具审批，CLI 会直接在终端内联显示审批内容，包括原因、命令和工作目录，并给出三种选择：
  `1` 或 `y/yes` 表示仅允许这一次，
  `2` 表示当前会话内对这条相同命令自动允许，
  `3`、`n/no` 或直接回车表示拒绝；不需要再手动敲 `/approvals grant|deny`。
- `--output json` 或显式 `approvals` 子命令仍保留 transport/action 控制面，适合脚本、外部 UI 或调试场景。
- 如果需要保留结构化 stdout 给脚本消费，使用 `--output json`。

JSON 行结构（简化）：

- 日志：`{"type":"log","level":"info|warn|ok|error","message":"..."}`
- 事件：`{"type":"event","event":"header|mode|plan_preview|transport","data":{...}}`
- 结果：`{"type":"result","data":{...}}`

重要说明：

- 当前 `--output json` 是 **现有 automation schema**，适合脚本、调试和外部 UI 做轻量集成。
- 它**不是**未来宿主编排协议的稳定承诺；当前输出仍缺少版本化 envelope、`run_id/seq` 等宿主级关联字段。
- 如果目标是“像主流 agent CLI 一样被外部宿主长期稳定托管”，当前可以使用 `run/script --headless` 获取 versioned event envelope，并通过 `--control-stdin` 使用显式 capability discovery / control actions；`--output json` 仍然只是 legacy automation schema，不是长期宿主协议。

## 宿主编排说明（当前状态）

Issue #135 对应的宿主编排能力目前分成“已落地”和“未落地”两层：

已落地：

- `run` / `script` 支持显式 `--headless`
- headless stdout 使用独立的 versioned event envelope：
  - 顶层字段：`schema_version`、`ts`、`session_id`、`run_id`、`seq`、`event`、`data`
  - 最小事件集：`session.started`、`task.started`、`task.completed`、`task.failed`
  - 已接通的运行时事件：`approval.pending`、`approval.resolved`、`tool.invoke`、`tool.result`、`tool.error`、`model.response`
- `chat` 不支持 `--headless`
- `--headless` 不能与 legacy `--output json` 混用
- `run` / `script --headless` 支持可选 `--control-stdin`
  - 控制响应使用独立 schema：`client-control-stdin.v1`
  - 当前已接通：`actions:list`、`status:get`、`approvals:list/poll/grant/deny/revoke`、`mcp:list/reload/show-tool`、`skills:list`
  - `mcp:unload` 仍然不是宿主协议 action；宿主发送时会得到结构化 `UNSUPPORTED_ACTION`
  - 未支持或未完成的 action 会返回结构化 error，而不是回落到 prompt 文案

仍未落地：

- 启动即发送的 capability handshake

当前推荐边界是：

1. 自动化脚本仍使用 `run/script --output json`。
2. 宿主事件流接入使用 `run/script --headless`。
3. 运行中控制当前优先使用 `--control-stdin` 做 `actions:list`、`status:get`、approvals、MCP 与 `skills:list`。
4. 不要把当前 `log/event/result` 三类 JSON 行当作长期稳定的宿主协议。

补充说明：

- `script --headless` 与 `run --headless` 一样支持审批超时控制。
- `script` 可显式传入 `--approval-timeout-seconds <seconds>`；未显式传入时，headless 脚本默认使用 `120s` 超时，避免无头会话无限等待审批。
- 启动即发送的 capability handshake 当前不属于 v1 计划；宿主应通过显式 `actions:list` 获取支持矩阵。

退出码约定：

- `0`：成功
- `1`：执行失败
- `2`：参数错误
- `3`：诊断或配置检查失败
- `130`：中断退出

说明：`script` 模式下只要任一任务失败，最终退出码为 `1`。

`run` 模式若触发工具审批并超过 `--approval-timeout-seconds`，会以失败退出，避免长时间无反馈阻塞。

`script --headless` 也遵循相同的超时失败语义；超时后会输出结构化 `task.failed` 事件并以失败退出。

`run` 模式可使用：
- `--auto-approve`：启用内置低风险工具自动审批名单。
- `--auto-approve-tool <name>`：追加指定工具到自动审批名单（可重复传入）。
