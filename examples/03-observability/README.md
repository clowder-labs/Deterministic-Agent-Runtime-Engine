# 03-observability

演示基于 OpenTelemetry 的可观测性接入。

## 运行

```bash
cd examples/03-observability
export OPENROUTER_API_KEY="your-api-key"
# 可选：指定模型
export OPENROUTER_MODEL="z-ai/glm-4.7"
# 可选：限制最大输出 tokens
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

## 输出示例

执行后可看到两类输出：
- Recorder 汇总（spans/metrics）
- OpenTelemetry console exporter 输出（如启用）

## 适用场景

- 验证可观测性接入
- 采集 token / context / tool 等关键指标
- 本地调试 telemetry 输出
