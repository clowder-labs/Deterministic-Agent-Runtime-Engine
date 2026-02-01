"""Observability domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpanKind(Enum):
    """Span kinds following OTel conventions."""

    INTERNAL = "internal"
    CLIENT = "client"
    SERVER = "server"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class GenAIOperation(Enum):
    """GenAI operation names per OTel semantic conventions."""

    CHAT = "chat"
    TEXT_COMPLETION = "text_completion"
    EMBEDDINGS = "embeddings"
    CREATE_AGENT = "create_agent"
    INVOKE_AGENT = "invoke_agent"
    EXECUTE_TOOL = "execute_tool"


class SpanStatus(Enum):
    """Span status values."""

    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class TokenUsage:
    """Token usage tracking per OTel gen_ai.usage attributes."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0


@dataclass
class SpanContext:
    """Context for distributed tracing."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    trace_flags: int = 0


@dataclass
class TelemetryConfig:
    """Configuration for telemetry providers."""

    # Service identity
    service_name: str = "dare-framework"
    service_version: str = "1.0.0"
    deployment_environment: str = "production"

    # Enable/disable
    enabled: bool = True

    # Exporter configuration
    exporter_type: str = "console"  # console, otlp, none
    otlp_endpoint: str | None = None
    otlp_headers: dict[str, str] = field(default_factory=dict)

    # Sampling
    sample_rate: float = 1.0

    # Privacy
    capture_content: bool = False

    # Resource tags
    resource_attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class RunMetrics:
    """Aggregated metrics for a single agent run."""

    # Token tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cached_tokens: int = 0

    # Context tracking
    max_context_length: int = 0
    max_messages_count: int = 0
    max_tools_count: int = 0

    # Tool tracking
    tool_calls_total: int = 0
    tool_calls_success: int = 0
    tool_calls_failed: int = 0
    tool_by_name: dict[str, int] = field(default_factory=dict)

    # Loop tracking
    model_invocations: int = 0
    execute_iterations: int = 0
    milestone_attempts: int = 0
    milestone_success: int = 0
    plan_attempts: int = 0
    plan_success: int = 0

    # Timing (seconds)
    total_duration: float = 0.0
    model_duration: float = 0.0
    tool_duration: float = 0.0

    # Budget tracking
    budget_tokens_used: int = 0
    budget_tokens_limit: int | None = None
    budget_cost_used: float = 0.0

    # Error tracking
    errors_total: int = 0
    errors_by_type: dict[str, int] = field(default_factory=dict)

    def record_tokens(self, input_tokens: int, output_tokens: int, cached: int = 0) -> None:
        """Record token usage from a model call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.cached_tokens += cached

    def record_context(self, length: int, messages_count: int, tools_count: int = 0) -> None:
        """Record context size."""
        self.max_context_length = max(self.max_context_length, length)
        self.max_messages_count = max(self.max_messages_count, messages_count)
        self.max_tools_count = max(self.max_tools_count, tools_count)

    def record_tool_call(self, tool_name: str, success: bool) -> None:
        """Record a tool invocation."""
        self.tool_calls_total += 1
        if success:
            self.tool_calls_success += 1
        else:
            self.tool_calls_failed += 1
        self.tool_by_name[tool_name] = self.tool_by_name.get(tool_name, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "tokens": {
                "input": self.total_input_tokens,
                "output": self.total_output_tokens,
                "total": self.total_input_tokens + self.total_output_tokens,
                "cached": self.cached_tokens,
            },
            "context": {
                "max_length": self.max_context_length,
                "max_messages": self.max_messages_count,
                "max_tools": self.max_tools_count,
            },
            "tools": {
                "total": self.tool_calls_total,
                "success": self.tool_calls_success,
                "failed": self.tool_calls_failed,
                "by_name": self.tool_by_name,
            },
            "loops": {
                "model_invocations": self.model_invocations,
                "execute_iterations": self.execute_iterations,
                "milestone_attempts": self.milestone_attempts,
                "milestone_success": self.milestone_success,
                "plan_attempts": self.plan_attempts,
                "plan_success": self.plan_success,
            },
            "timing": {
                "total_seconds": self.total_duration,
                "model_seconds": self.model_duration,
                "tool_seconds": self.tool_duration,
            },
            "budget": {
                "tokens_used": self.budget_tokens_used,
                "tokens_limit": self.budget_tokens_limit,
                "cost_used": self.budget_cost_used,
            },
            "errors": {
                "total": self.errors_total,
                "by_type": self.errors_by_type,
            },
        }


__all__ = [
    "SpanKind",
    "GenAIOperation",
    "SpanStatus",
    "TokenUsage",
    "SpanContext",
    "TelemetryConfig",
    "RunMetrics",
]
