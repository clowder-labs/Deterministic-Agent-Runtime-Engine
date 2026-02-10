from __future__ import annotations

from typing import Any

import pytest

from dare_framework.agent import BaseAgent
from dare_framework.config.types import ComponentConfig, Config
from dare_framework.infra.component import ComponentType
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import ModelInput, ModelResponse, Prompt
from dare_framework.skill.types import Skill
from dare_framework.tool.tool_manager import ToolManager


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
    for tool_item in agent.context.list_tools():
        if isinstance(tool_item, dict):
            metadata = tool_item.get("metadata", {})
            display_name = metadata.get("display_name")
            if isinstance(display_name, str):
                names.add(display_name)
            continue

        # Compatibility: some code paths return CapabilityDescriptor objects.
        metadata = getattr(tool_item, "metadata", {}) or {}
        display_name = metadata.get("display_name") if isinstance(metadata, dict) else None
        if isinstance(display_name, str):
            names.add(display_name)
            continue

        descriptor_name = getattr(tool_item, "name", None)
        if isinstance(descriptor_name, str):
            names.add(descriptor_name)
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
    assert "skill" not in tool_names

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
    assert "skill" in tool_names

    assembled = agent.context.assemble()
    assert assembled.sys_prompt is not None
    assert "## Skill: ManualSkill" not in assembled.sys_prompt.content


@pytest.mark.asyncio
async def test_builder_auto_injects_default_workspace_tools() -> None:
    agent = await (
        BaseAgent.simple_chat_agent_builder("defaults-on")
        .with_model(DummyModelAdapter())
        .with_prompt(_base_prompt())
        .with_skill_tool(False)
        .build()
    )

    tool_names = _tool_names(agent)
    assert {"read_file", "write_file", "search_code", "search_file", "run_command", "run_cmd"} <= tool_names


@pytest.mark.asyncio
async def test_builder_default_workspace_tools_respect_component_disable() -> None:
    config = Config(
        workspace_dir="/tmp",
        user_dir="/tmp",
        components={
            ComponentType.TOOL.value: ComponentConfig(
                disabled=["run_command", "run_cmd", "search_file"]
            )
        },
    )

    agent = await (
        BaseAgent.simple_chat_agent_builder("defaults-filtered")
        .with_model(DummyModelAdapter())
        .with_prompt(_base_prompt())
        .with_skill_tool(False)
        .with_config(config)
        .build()
    )

    tool_names = _tool_names(agent)
    assert "run_command" not in tool_names
    assert "run_cmd" not in tool_names
    assert "search_file" not in tool_names
    assert "read_file" in tool_names


@pytest.mark.asyncio
async def test_builder_with_custom_gateway_does_not_auto_inject_defaults() -> None:
    agent = await (
        BaseAgent.simple_chat_agent_builder("defaults-off")
        .with_model(DummyModelAdapter())
        .with_prompt(_base_prompt())
        .with_skill_tool(False)
        .with_tool_gateway(ToolManager(load_entrypoints=False))
        .build()
    )

    tool_names = _tool_names(agent)
    assert "read_file" not in tool_names
    assert "write_file" not in tool_names
