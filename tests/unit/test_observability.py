"""Tests for observability instrumentation."""

from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import DareAgent
from dare_framework.config.types import ObservabilityConfig, RedactionConfig
from dare_framework.observability._internal.in_memory_provider import InMemoryTelemetryProvider
from dare_framework.observability.types import TelemetryMetricNames, TelemetrySpanNames
from dare_framework.hook.types import HookPhase
from dare_framework.model.types import ModelInput, ModelResponse


class MockModelAdapter:
    """Mock model adapter for testing telemetry."""

    def __init__(self, response: ModelResponse | None = None) -> None:
        self.response = response or ModelResponse(content="ok", tool_calls=[])

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        return self.response


class MockPlanner:
    async def plan(self, ctx: Any) -> Any:
        from dare_framework.plan.types import ProposedPlan

        return ProposedPlan(plan_description="plan", steps=[], attempt=1)


class MockValidator:
    async def validate_plan(self, plan: Any, ctx: Any) -> Any:
        from dare_framework.plan.types import ValidatedPlan

        return ValidatedPlan(success=True, plan_description=plan.plan_description, steps=[], errors=[])

    async def verify_milestone(self, result: Any, ctx: Any) -> Any:
        from dare_framework.plan.types import VerifyResult

        return VerifyResult(success=True, errors=[])


@pytest.mark.asyncio
async def test_telemetry_span_structure_for_five_layer_run() -> None:
    provider = InMemoryTelemetryProvider()
    model = MockModelAdapter()
    agent = DareAgent(
        name="telemetry-agent",
        model=model,
        planner=MockPlanner(),
        validator=MockValidator(),
        telemetry_providers=[provider],
    )

    await agent.run("test task")

    span_names = [span["name"] for span in provider.spans]
    assert TelemetrySpanNames.RUN in span_names
    assert TelemetrySpanNames.SESSION in span_names
    assert TelemetrySpanNames.MILESTONE in span_names
    assert TelemetrySpanNames.PLAN in span_names
    assert TelemetrySpanNames.EXECUTE in span_names
    assert TelemetrySpanNames.MODEL in span_names


@pytest.mark.asyncio
async def test_metrics_emitted_for_context_and_tokens() -> None:
    provider = InMemoryTelemetryProvider()
    response = ModelResponse(
        content="ok",
        tool_calls=[],
        usage={"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
    )
    model = MockModelAdapter(response=response)
    agent = DareAgent(
        name="metrics-agent",
        model=model,
        telemetry_providers=[provider],
    )

    await agent.run("metrics task")

    metric_names = {metric["name"] for metric in provider.metrics}
    assert TelemetryMetricNames.CONTEXT_MESSAGES_COUNT in metric_names
    assert TelemetryMetricNames.CONTEXT_TOKENS_ESTIMATE in metric_names
    assert TelemetryMetricNames.MODEL_TOKENS_INPUT in metric_names
    assert TelemetryMetricNames.MODEL_TOKENS_OUTPUT in metric_names
    assert TelemetryMetricNames.MODEL_TOKENS_TOTAL in metric_names


@pytest.mark.asyncio
async def test_redaction_applied_by_default() -> None:
    redaction = RedactionConfig(mode="denylist", keys=["prompt"], replacement="[REDACTED]")
    config = ObservabilityConfig(enabled=True, capture_content=False, redaction=redaction)
    provider = InMemoryTelemetryProvider(config=config)

    await provider.invoke(HookPhase.BEFORE_MODEL, payload={"prompt": "secret", "safe": "ok"})

    _, payload = provider.hook_events[-1]
    assert payload["prompt"] == "[REDACTED]"
    assert payload["safe"] == "ok"
