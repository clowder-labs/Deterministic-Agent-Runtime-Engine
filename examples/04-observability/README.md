# 04-observability

演示基于 OpenTelemetry 的可观测性接入，并用内存 TelemetryProvider 输出 span/metrics 结果。

## 运行

```bash
cd examples/04-observability
export OPENROUTER_API_KEY="your-api-key"
# 可选：指定模型
export OPENROUTER_MODEL="z-ai/glm-4.7"
# 可选：限制最大输出 tokens
export OPENROUTER_MAX_TOKENS="2048"
python main.py
```

## 代码要点

- 通过 `ObservabilityConfig` 启用 telemetry。
- 用 `add_telemetry_providers()` 注入 TelemetryProvider（示例中为 InMemory）。
- 如果本地安装了 OpenTelemetry SDK，并设置 `exporter: console`，控制台会打印 trace。

```python
observability = ObservabilityConfig(enabled=True, exporter="console")
config = Config(observability=observability)

telemetry_provider = InMemoryTelemetryProvider(config=observability)
providers = create_default_telemetry_providers(config, service_name="dare-observability-demo")
providers.append(telemetry_provider)

agent = (
    DareAgentBuilder("observability-demo")
    .with_config(config)
    .with_model(model_adapter)
    .add_telemetry_providers(*providers)
    .build()
)
```

## 输出示例

执行后会打印：
- spans 列表（如 `dare.run`, `dare.execute`, `dare.model`）
- metrics 列表（如 `context.tokens.estimate`, `model.tokens.total`）

## 适用场景

- 验证可观测性接入
- 采集 token / context / tool 等关键指标
- 本地调试 telemetry 输出
