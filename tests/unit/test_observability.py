"""Tests for observability instrumentation."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

import pytest

from dare_framework.agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.observability._internal.tracing_hook import ObservabilityHook
from dare_framework.observability.kernel import ITelemetryProvider
from dare_framework.infra.component import ComponentType
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.tool.types import ToolResult


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

    async def decompose(self, task: Any, ctx: Any) -> Any:
        _ = ctx
        from dare_framework.plan.types import DecompositionResult, Milestone

        return DecompositionResult(
            milestones=[
                Milestone(
                    milestone_id=f"{getattr(task, 'task_id', 'task')}_m1",
                    description=getattr(task, "description", "task"),
                    user_input=getattr(task, "description", "task"),
                )
            ],
            reasoning="mock decomposition",
        )


class MockValidator:
    async def validate_plan(self, plan: Any, ctx: Any) -> Any:
        from dare_framework.plan.types import ValidatedPlan

        return ValidatedPlan(success=True, plan_description=plan.plan_description, steps=[], errors=[])

    async def verify_milestone(self, result: Any, ctx: Any, *, plan: Any | None = None) -> Any:
        _ = plan
        from dare_framework.plan.types import VerifyResult

        return VerifyResult(success=True, errors=[])


class NoopToolGateway:
    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope, params)
        return ToolResult(success=False, output={}, error="unexpected invoke")


class RecordingSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attributes: dict[str, Any] = {}
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.status: tuple[str, str | None] | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append((name, attributes or {}))

    def set_status(self, status: str, description: str | None = None) -> None:
        self.status = (status, description)

    def end(self) -> None:
        return None


class RecordingTelemetryProvider(ITelemetryProvider):
    def __init__(self) -> None:
        self.spans: list[RecordingSpan] = []
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
    ) -> Generator[RecordingSpan | None, None, None]:
        span = RecordingSpan(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
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
        return None

    def shutdown(self) -> None:
        return None


@pytest.mark.asyncio
async def test_telemetry_span_structure_for_five_layer_run() -> None:
    provider = RecordingTelemetryProvider()
    hook = ObservabilityHook(provider)
    model = MockModelAdapter()
    agent = DareAgent(
        name="telemetry-agent",
        model=model,
        context=Context(config=Config()),
        tool_gateway=NoopToolGateway(),
        planner=MockPlanner(),
        validator=MockValidator(),
        telemetry=provider,
        hooks=[hook],
    )

    await agent("test task")

    span_names = [span.name for span in provider.spans]
    assert "dare.session" in span_names
    assert "dare.milestone" in span_names
    assert "dare.plan" in span_names
    assert "dare.execute" in span_names
    assert "llm.chat" in span_names


@pytest.mark.asyncio
async def test_metrics_emitted_for_context_and_tokens() -> None:
    provider = RecordingTelemetryProvider()
    hook = ObservabilityHook(provider)
    response = ModelResponse(
        content="ok",
        tool_calls=[],
        usage={"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
    )
    model = MockModelAdapter(response=response)
    agent = DareAgent(
        name="metrics-agent",
        model=model,
        context=Context(config=Config()),
        tool_gateway=NoopToolGateway(),
        telemetry=provider,
        hooks=[hook],
    )

    await agent("metrics task")

    metric_names = {metric["name"] for metric in provider.metrics}
    assert "gen_ai.client.token.usage" in metric_names
    assert "dare.context.length" in metric_names
