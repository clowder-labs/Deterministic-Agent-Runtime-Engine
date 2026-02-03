# 03-observability

在 02 的基础上加入 OpenTelemetry 可观测性，聚焦埋点、指标与输出汇总（本示例不强调工具调用）。

## 运行

```bash
cd examples/03-observability
export OPENROUTER_API_KEY="your-api-key"
# 可选：指定模型
export OPENROUTER_MODEL="z-ai/glm-4.7"
# 可选：限制最大输出 tokens，避免信用不足错误
export OPENROUTER_MAX_TOKENS="2048"
python main.py
```

## 代码要点

- 使用 `TelemetryConfig` 初始化 `OTelTelemetryProvider`。
- 通过 `with_telemetry()` 注入 TelemetryProvider，并显式加入 `ObservabilityHook`。
- 示例内置 `RecordingTelemetryProvider`，运行结束后打印 spans/metrics 汇总。
- 如果本地安装了 OpenTelemetry SDK，并设置 `exporter_type=console`，控制台会打印 trace/metrics。

```python
telemetry_config = TelemetryConfig(
    service_name="dare-observability-demo",
    exporter_type="console",
)
telemetry = OTelTelemetryProvider(telemetry_config)
hook = ObservabilityHook(telemetry)

builder = (
    DareAgentBuilder("observability-demo")
    .with_model(model_adapter)
    .with_telemetry(telemetry)
    .add_hooks(hook)
)
agent = await builder.build()
```

## 进阶点

- 相对 02，新增可观测性：TelemetryProvider + ObservabilityHook
- 内置 `RecordingTelemetryProvider`，结束后打印 spans/metrics 汇总
- 若安装 OTel SDK 且设置 `exporter_type=console`，控制台会输出 trace/metrics
- 示例聚焦观测，不展示工具调用（如需工具可参考 02）

## Prompt 管理

系统提示由框架 Prompt Store 管理（默认 `base.system`），无需在示例中手写系统提示。
如需覆盖，使用 `.dare/_prompts.json` 配置。

## 文件结构

```
03-observability/
├── main.py
└── README.md
```

## 适用场景

- 验证可观测性接入
- 采集 token / context / tool 等关键指标
- 本地调试 telemetry 输出
