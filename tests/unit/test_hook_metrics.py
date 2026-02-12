from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

import pytest

from dare_framework.hook.types import HookPhase
from dare_framework.infra.component import ComponentType
from dare_framework.observability._internal.tracing_hook import ObservabilityHook
from dare_framework.observability.kernel import ITelemetryProvider


class _Span:
    def set_attribute(self, key: str, value: Any) -> None:
        _ = (key, value)

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        _ = (name, attributes)

    def set_status(self, status: str, description: str | None = None) -> None:
        _ = (status, description)

    def end(self) -> None:
        return None


class _RecordingTelemetry(ITelemetryProvider):
    def __init__(self) -> None:
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
    ) -> Generator[_Span, None, None]:
        _ = (name, kind, attributes)
        yield _Span()

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.metrics.append({"name": name, "value": value, "attributes": attributes or {}})

    def record_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        _ = (name, attributes)

    def shutdown(self) -> None:
        return None


@pytest.mark.asyncio
async def test_hook_overhead_metric_emitted() -> None:
    telemetry = _RecordingTelemetry()
    hook = ObservabilityHook(telemetry)

    await hook.invoke(
        HookPhase.BEFORE_RUN,
        payload={
            "task_id": "t1",
            "session_id": "s1",
            "agent_name": "agent",
            "execution_mode": "five_layer",
        },
    )
    await hook.invoke(HookPhase.BEFORE_MODEL, payload={"iteration": 1, "model_name": "mock"})
    await hook.invoke(
        HookPhase.AFTER_MODEL,
        payload={"model_usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
    )
    await hook.invoke(
        HookPhase.AFTER_RUN,
        payload={"success": True, "errors": [], "token_usage": {"input_tokens": 1, "output_tokens": 1}},
    )

    metric_names = {metric["name"] for metric in telemetry.metrics}
    assert "hook.overhead_ratio" in metric_names
