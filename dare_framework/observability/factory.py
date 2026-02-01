"""Factories for observability components."""

from __future__ import annotations

from dare_framework.config.types import Config, ObservabilityConfig
from dare_framework.observability._internal.otel_provider import OpenTelemetryProvider
from dare_framework.observability.kernel import ITelemetryProvider


def create_default_telemetry_providers(
    config: Config | ObservabilityConfig,
    *,
    service_name: str = "dare-runtime",
) -> list[ITelemetryProvider]:
    """Create default telemetry providers based on configuration."""
    observability = config.observability if isinstance(config, Config) else config
    if not observability.enabled:
        return []
    provider = OpenTelemetryProvider(observability, service_name=service_name)
    # Provider may no-op if OpenTelemetry SDK is unavailable.
    return [provider]


__all__ = ["create_default_telemetry_providers"]
