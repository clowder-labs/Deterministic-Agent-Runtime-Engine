from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent
from dare_framework.config.types import Config
from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse, Prompt
from dare_framework.skill.types import Skill


class DummyModelAdapter(IModelAdapter):
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
        return ModelResponse(content="ok")


def _base_prompt() -> Prompt:
    return Prompt(
        prompt_id="test.system",
        role="system",
        content="base prompt",
        supported_models=["*"],
        order=0,
    )


def _manual_skill() -> Skill:
    return Skill(
        id="manual-skill",
        name="ManualSkill",
        description="manual",
        content="manual skill content",
    )


def _tool_names(agent: Any) -> set[str]:
    names: set[str] = set()
    for tool_def in agent.context.list_tools():
        metadata = tool_def.get("metadata", {})
        display_name = metadata.get("display_name")
        if isinstance(display_name, str):
            names.add(display_name)
    return names


@pytest.mark.asyncio
async def test_builder_skill_tool_false_preserves_sys_skill_and_skips_search_tool() -> None:
    agent = await (
        BaseAgent.simple_chat_agent_builder("skill-off")
        .with_model(DummyModelAdapter())
        .with_prompt(_base_prompt())
        .with_sys_skill(_manual_skill())
        .with_skill_tool(False)
        .build()
    )

    tool_names = _tool_names(agent)
    assert "search_skill" not in tool_names

    assembled = agent.context.assemble()
    assert assembled.sys_prompt is not None
    assert "## Skill: ManualSkill" in assembled.sys_prompt.content


@pytest.mark.asyncio
async def test_builder_skill_tool_true_registers_search_tool_and_ignores_sys_skill() -> None:
    agent = await (
        BaseAgent.simple_chat_agent_builder("skill-on")
        .with_model(DummyModelAdapter())
        .with_prompt(_base_prompt())
        .with_sys_skill(_manual_skill())
        .with_skill_tool(True)
        .with_config(Config(workspace_dir="/tmp", user_dir="/tmp"))
        .build()
    )

    tool_names = _tool_names(agent)
    assert "search_skill" in tool_names

    assembled = agent.context.assemble()
    assert assembled.sys_prompt is not None
    assert "## Skill: ManualSkill" not in assembled.sys_prompt.content
