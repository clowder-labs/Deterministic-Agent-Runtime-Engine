"""Observability example using DareAgentBuilder + OpenTelemetry."""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import DareAgentBuilder
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.observability._internal.otel_provider import (
    OTEL_AVAILABLE,
    OTelTelemetryProvider,
)
from dare_framework.observability._internal.tracing_hook import ObservabilityHook
from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.observability.types import TelemetryConfig
from dare_framework.infra.component import ComponentType


class RecordingTelemetryProvider(ITelemetryProvider):
    def __init__(self) -> None:
        self.spans: list[dict[str, Any]] = []
        self.metrics: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "recording"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.HOOK

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        kind: str = "internal",
        attributes: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any] | None, None, None]:
        span = {"name": name, "attributes": attributes or {}, "kind": kind}
        self.spans.append(span)
        yield span

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.metrics.append({"name": name, "value": value, "attributes": attributes or {}})

    def record_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        return

    def shutdown(self) -> None:
        return


async def main() -> None:
    """Run a single-turn agent with telemetry enabled."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)

    model_name = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.5-air:free")
    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))

    model_adapter = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
    )

    telemetry_config = TelemetryConfig(
        service_name="dare-observability-demo",
        service_version="1.0.0",
        deployment_environment=os.getenv("DARE_ENV", "development"),
        enabled=True,
        exporter_type=os.getenv("DARE_OTEL_EXPORTER", "console"),
        otlp_endpoint=os.getenv("DARE_OTEL_OTLP_ENDPOINT"),
    )
    telemetry = OTelTelemetryProvider(telemetry_config)
    hook = ObservabilityHook(telemetry)
    recorder = RecordingTelemetryProvider()

    builder = (
        DareAgentBuilder("observability-demo")
        .with_model(model_adapter)
        .with_telemetry(telemetry)
        .add_hooks(hook, ObservabilityHook(recorder))
    )
    agent = await builder.build()

    result = await agent("Summarize the DARE framework in one sentence.")
    print(f"\nAssistant: {result.output}\n")
    if not OTEL_AVAILABLE:
        print("OpenTelemetry SDK not available; telemetry disabled")
    else:
        print("Telemetry enabled. Check console exporter output for spans/metrics.")

    span_names = [span["name"] for span in recorder.spans]
    metric_names = sorted({metric["name"] for metric in recorder.metrics})

    print("\nCollected spans (names):")
    print("  " + ", ".join(span_names))
    print("\nCollected spans (data):")
    for span in recorder.spans:
        print(
            f"  - name={span.get('name')}, "
            f"attrs={span.get('attributes')}"
        )

    print("\nCollected metrics (names):")
    print("  " + ", ".join(metric_names))
    print("\nCollected metrics (data):")
    for metric in recorder.metrics:
        print(f"  - {metric.get('name')}: {metric.get('value')} ({metric.get('attributes')})")
    


if __name__ == "__main__":
    asyncio.run(main())
