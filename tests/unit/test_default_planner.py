from __future__ import annotations

from typing import Any

import pytest

from dare_framework.config import Config
from dare_framework.context import AttachmentRef, Context, Message
from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan._internal.default_planner import DefaultPlanner
from dare_framework.plan.types import Task


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
    ctx = Context(id="planner-test", config=Config())
    ctx.stm_add(Message(role="user", text="do something"))

    plan = await planner.plan(ctx)

    assert plan.plan_description == "demo"
    assert model.last_input is not None
    assert len(model.last_input.messages) == 2


@pytest.mark.asyncio
async def test_default_planner_decompose_prefers_task_input_message_text() -> None:
    model = DummyModelAdapter()
    planner = DefaultPlanner(model)
    ctx = Context(id="planner-decompose-test", config=Config())
    task = Task(
        description="fallback-description",
        input_message=Message(role="user", text="canonical-input"),
    )

    decomposition = await planner.decompose(task, ctx)

    assert decomposition.milestones[0].user_input == "canonical-input"


@pytest.mark.asyncio
async def test_default_planner_uses_attachment_fallback_for_empty_message_text() -> None:
    model = DummyModelAdapter()
    planner = DefaultPlanner(model)
    ctx = Context(id="planner-attachment-only", config=Config())
    ctx.stm_add(
        Message(
            role="user",
            text=None,
            attachments=[AttachmentRef(uri="data:image/png;base64,cG5n")],
        )
    )

    await planner.plan(ctx)

    assert model.last_input is not None
    assert model.last_input.messages[1].text.startswith("Task: [User provided 1 attachment(s) with no text input]")
