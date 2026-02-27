from __future__ import annotations

from typing import Any

from dare_framework.agent import BaseAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.security.impl import NoOpSecurityBoundary, PolicySecurityBoundary
from dare_framework.tool.types import ToolResult


class _Model:
    name = "mock-model"

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        return ModelResponse(content="ok", tool_calls=[])


class _ToolGateway:
    def list_capabilities(self) -> list[Any]:
        return []

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        _ = (capability_id, envelope, params)
        return ToolResult(success=True, output={})


def test_dare_builder_defaults_to_policy_security_boundary() -> None:
    builder = BaseAgent.dare_agent_builder("security-default").with_model(_Model())
    config = Config()
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert isinstance(agent._security_boundary, PolicySecurityBoundary)


def test_dare_builder_supports_noop_boundary_from_config() -> None:
    builder = BaseAgent.dare_agent_builder("security-noop").with_model(_Model())
    config = Config.from_dict({"security": {"boundary": "noop"}})
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert isinstance(agent._security_boundary, NoOpSecurityBoundary)


def test_dare_builder_explicit_security_boundary_overrides_config() -> None:
    explicit = NoOpSecurityBoundary()
    builder = BaseAgent.dare_agent_builder("security-explicit").with_model(_Model())
    builder = builder.with_security_boundary(explicit)
    config = Config.from_dict({"security": {"boundary": "policy"}})
    agent = builder._build_impl(  # noqa: SLF001 - builder contract test
        config=config,
        model=_Model(),
        context=Context(config=config),
        tool_gateway=_ToolGateway(),
        approval_manager=None,
        agent_channel=None,
    )

    assert agent._security_boundary is explicit
