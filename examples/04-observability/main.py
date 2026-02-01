"""Observability example using DareAgentBuilder + TelemetryProvider.

This example emits telemetry via an in-memory provider and optionally via
OpenTelemetry (if the SDK is installed and exporter is configured).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import DareAgentBuilder
from dare_framework.config import Config, ObservabilityConfig, RedactionConfig
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.observability import create_default_telemetry_providers
from dare_framework.observability._internal.in_memory_provider import InMemoryTelemetryProvider


async def main() -> None:
    """Run a single-turn agent with telemetry enabled."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)

    model_name = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.5-air:free")
    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))

    observability = ObservabilityConfig(
        enabled=True,
        exporter="console",  # console | otlp | none
        capture_content=False,
        redaction=RedactionConfig(mode="denylist", keys=["prompt", "content", "arguments"]),
    )
    config = Config(observability=observability)

    model_adapter = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
    )

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

    result = await agent.run("Summarize the DARE framework in one sentence.")
    print(f"\nAssistant: {result.output}\n")

    span_names = [span["name"] for span in telemetry_provider.spans]
    metric_names = sorted({metric["name"] for metric in telemetry_provider.metrics})

    print("Collected spans (names):")
    print("  " + ", ".join(span_names))
    print("\nCollected spans (data):")
    for span in telemetry_provider.spans:
        print(
            f"  - name={span.get('name')}, "
            f"parent={span.get('parent')}, "
            f"attrs={span.get('attributes')}"
        )

    print("\nCollected metrics (names):")
    print("  " + ", ".join(metric_names))
    print("\nCollected metrics (data):")
    for metric in telemetry_provider.metrics:
        print(f"  - {metric.get('name')}: {metric.get('value')}")
    


if __name__ == "__main__":
    asyncio.run(main())
