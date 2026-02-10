from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent
from dare_framework.config.types import Config
from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse, Prompt
from dare_framework.skill._internal.action_handler import SkillsActionHandler
from dare_framework.skill.interfaces import ISkillStore
from dare_framework.skill.types import Skill
from dare_framework.tool.tool_manager import ToolManager
from dare_framework.transport import AgentChannel, ResourceAction, TransportEnvelope

SKILL_TOOL_NAME = "skill"


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


class DummyClientChannel:
    def __init__(self) -> None:
        self._sender = None

    def attach_agent_envelope_sender(self, sender):
        self._sender = sender

    def agent_envelope_receiver(self):
        async def receiver(_msg: TransportEnvelope) -> None:
            return None

        return receiver


class InMemorySkillStore(ISkillStore):
    def __init__(self, skills: list[Skill]) -> None:
        self._skills = list(skills)

    def list_skills(self) -> list[Skill]:
        return list(self._skills)

    def get_skill(self, skill_id: str) -> Skill | None:
        for skill in self._skills:
            if skill.id == skill_id:
                return skill
        return None

    def select_for_task(self, query: str, limit: int = 5) -> list[Skill]:
        lowered = query.lower()
        hits = [skill for skill in self._skills if lowered in skill.id.lower() or lowered in skill.name.lower()]
        return hits[:limit]


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


def _tool_names(agent: BaseAgent) -> set[str]:
    names: set[str] = set()
    for descriptor in agent.context.list_tools():
        metadata = descriptor.metadata
        if metadata is None:
            continue
        display_name = metadata.get("display_name")
        if isinstance(display_name, str) and display_name:
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
    assert SKILL_TOOL_NAME not in tool_names

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
    assert SKILL_TOOL_NAME in tool_names

    assembled = agent.context.assemble()
    assert assembled.sys_prompt is not None
    assert "## Skill: ManualSkill" not in assembled.sys_prompt.content


@pytest.mark.asyncio
async def test_builder_reuses_resolved_skill_store_for_tool_and_action_handler() -> None:
    store = InMemorySkillStore([_manual_skill()])
    channel = AgentChannel.build(DummyClientChannel())
    agent = await (
        BaseAgent.simple_chat_agent_builder("skill-shared")
        .with_model(DummyModelAdapter())
        .with_prompt(_base_prompt())
        .with_config(Config(workspace_dir="/tmp", user_dir="/tmp"))
        .with_skill_store(store)
        .with_agent_channel(channel)
        .with_skill_tool(True)
        .build()
    )

    gateway = getattr(agent.context, "_tool_gateway", None)
    assert isinstance(gateway, ToolManager)
    skill_tools = [tool for tool in gateway.list_tools() if tool.name == "skill"]
    assert len(skill_tools) == 1
    assert getattr(skill_tools[0], "_skill_store") is store

    dispatcher = channel.get_action_handler_dispatcher()
    assert dispatcher is not None
    skills_handler = dispatcher._action_handlers.get(ResourceAction.SKILLS_LIST)  # type: ignore[attr-defined]
    assert isinstance(skills_handler, SkillsActionHandler)
    assert getattr(skills_handler, "_store") is store
