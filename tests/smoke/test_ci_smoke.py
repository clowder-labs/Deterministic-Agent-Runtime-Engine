from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent
from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse, Prompt


class DummyModelAdapter(IModelAdapter):
    """Dummy model prevents any external model call during smoke checks."""

    @property
    def name(self) -> str:
        return "smoke-dummy"

    @property
    def model(self) -> str:
        return "smoke-dummy-model"

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.MODEL_ADAPTER

    async def generate(self, model_input: ModelInput, *, options: Any | None = None) -> ModelResponse:
        return ModelResponse(content="smoke-ok")


def _base_prompt() -> Prompt:
    return Prompt(
        prompt_id="smoke.system",
        role="system",
        content="smoke prompt",
        supported_models=["*"],
        order=0,
    )


async def _build_agent(name: str):
    return await (
        BaseAgent.simple_chat_agent_builder(name)
        .with_model(DummyModelAdapter())
        .with_prompt(_base_prompt())
        .build()
    )


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_smoke_builder_can_build_simple_chat_agent() -> None:
    agent = await _build_agent("smoke-builder")
    assert agent.name == "smoke-builder"


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_smoke_context_assemble_contains_prompt() -> None:
    agent = await _build_agent("smoke-context")
    assembled = agent.context.assemble()
    assert assembled.sys_prompt is not None
    assert "smoke prompt" in assembled.sys_prompt.content


@pytest.mark.smoke
def test_smoke_prompt_construction() -> None:
    prompt = _base_prompt()
    assert prompt.role == "system"
    assert prompt.content.startswith("smoke")
