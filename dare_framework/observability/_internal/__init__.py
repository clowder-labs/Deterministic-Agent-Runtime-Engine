"""Observability internal implementations (non-public).

Re-exports concrete helpers so the domain facade can import from
``dare_framework.observability._internal`` without reaching into leaf modules.
"""

from dare_framework.observability._internal.event_trace_bridge import (
    TraceAwareEventLog,
    TraceContext,
)
from dare_framework.observability._internal.llm_io_capture_hook import LLMIOCaptureHook
from dare_framework.observability._internal.metrics_collector import MetricsCollector
from dare_framework.observability._internal.otel_provider import (
    DAREAttributes,
    GenAIAttributes,
    NoOpTelemetryProvider,
    OTelTelemetryProvider,
)
from dare_framework.observability._internal.tracing_hook import ObservabilityHook

__all__ = [
    "DAREAttributes",
    "GenAIAttributes",
    "LLMIOCaptureHook",
    "MetricsCollector",
    "NoOpTelemetryProvider",
    "OTelTelemetryProvider",
    "ObservabilityHook",
    "TraceAwareEventLog",
    "TraceContext",
]
