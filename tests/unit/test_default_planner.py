from __future__ import annotations

from typing import Any

import pytest

from dare_framework.context import Context, Message
from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan._internal.default_planner import DefaultPlanner


class DummyModelAdapter(IModelAdapter):
    def __init__(self) -> None:
        self.last_input: ModelInput | None = None

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def model(self) -> str:
        return "dummy-model"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.MODEL_ADAPTER

    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        if not isinstance(model_input, ModelInput):
            raise TypeError("DefaultPlanner must pass ModelInput")
        self.last_input = model_input
        return ModelResponse(content='{"plan_description": "demo", "steps": []}')


@pytest.mark.asyncio
async def test_default_planner_uses_model_input() -> None:
    model = DummyModelAdapter()
    planner = DefaultPlanner(model)
    ctx = Context(id="planner-test")
    ctx.stm_add(Message(role="user", content="do something"))

    plan = await planner.plan(ctx)

    assert plan.plan_description == "demo"
    assert model.last_input is not None
    assert len(model.last_input.messages) == 2
