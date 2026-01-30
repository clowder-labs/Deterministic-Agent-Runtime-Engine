"""Unit tests for FiveLayerAgent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from dare_framework.agent import FiveLayerAgent
from dare_framework.context import Budget, Context, Message
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.tool.types import CapabilityDescriptor, CapabilityKind, CapabilityType


# =============================================================================
# Mock Components
# =============================================================================


class MockModelAdapter:
    """Mock model adapter for testing."""

    def __init__(self, responses: list[ModelResponse] | None = None) -> None:
        self.responses = responses or [
            ModelResponse(content="Hello! I'm a mock response.", tool_calls=[])
        ]
        self._call_idx = 0
        self.generate_calls: list[ModelInput] = []

    async def generate(
        self, model_input: ModelInput, *, options: Any = None
    ) -> ModelResponse:
        self.generate_calls.append(model_input)
        response = self.responses[self._call_idx % len(self.responses)]
        self._call_idx += 1
        return response


class MockPlanner:
    """Mock planner for testing."""

    def __init__(self) -> None:
        self.plan_calls = []

    async def plan(self, ctx: Any) -> Any:
        self.plan_calls.append(ctx)
        from dare_framework.plan.types import ProposedPlan
        return ProposedPlan(
            plan_description="Mock plan",
            steps=[],
            attempt=len(self.plan_calls),
        )


class MockValidator:
    """Mock validator for testing."""

    def __init__(self, validate_success: bool = True, verify_success: bool = True) -> None:
        self.validate_success = validate_success
        self.verify_success = verify_success
        self.validate_calls = []
        self.verify_calls = []

    async def validate_plan(self, plan: Any, ctx: Any) -> Any:
        self.validate_calls.append((plan, ctx))
        from dare_framework.plan.types import ValidatedPlan
        return ValidatedPlan(
            success=self.validate_success,
            plan_description=plan.plan_description,
            steps=[],
            errors=[] if self.validate_success else ["validation failed"],
        )

    async def verify_milestone(self, result: Any, ctx: Any) -> Any:
        self.verify_calls.append((result, ctx))
        from dare_framework.plan.types import VerifyResult
        return VerifyResult(
            success=self.verify_success,
            errors=[] if self.verify_success else ["verification failed"],
        )


class MockToolGateway:
    """Mock tool gateway for testing."""

    def __init__(self, capabilities: list[Any] | None = None) -> None:
        self.invoke_calls = []
        self._capabilities = list(capabilities or [])

    async def list_capabilities(self) -> list[Any]:
        return list(self._capabilities)

    async def invoke(self, capability_id: str, params: dict[str, Any], *, envelope: Any) -> Any:
        self.invoke_calls.append((capability_id, params, envelope))
        return MagicMock(success=True, output={"result": "mock"}, evidence=[])


class MockEventLog:
    """Mock event log for testing."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def append(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))


# =============================================================================
# Tests: Initialization
# =============================================================================


class TestFiveLayerAgentInit:
    """Tests for FiveLayerAgent initialization."""

    def test_init_with_minimal_deps(self) -> None:
        """Agent can be created with only required dependencies."""
        model = MockModelAdapter()
        agent = FiveLayerAgent(name="test-agent", model=model)

        assert agent.name == "test-agent"
        assert agent.context is not None
        assert not agent.is_full_five_layer_mode
        assert agent.is_simple_mode  # No planner, no tools

    def test_init_with_context(self) -> None:
        """Agent can use a provided context."""
        model = MockModelAdapter()
        context = Context(id="custom-context", budget=Budget(max_tokens=1000))
        agent = FiveLayerAgent(name="test-agent", model=model, context=context)

        assert agent.context.id == "custom-context"

    def test_init_with_planner_enables_five_layer_mode(self) -> None:
        """Providing a planner enables full five-layer mode."""
        model = MockModelAdapter()
        planner = MockPlanner()
        agent = FiveLayerAgent(name="test-agent", model=model, planner=planner)

        assert agent.is_full_five_layer_mode

    def test_init_with_all_deps(self) -> None:
        """Agent can be created with all dependencies."""
        model = MockModelAdapter()
        planner = MockPlanner()
        validator = MockValidator()
        tool_gateway = MockToolGateway()
        event_log = MockEventLog()

        agent = FiveLayerAgent(
            name="full-agent",
            model=model,
            planner=planner,
            validator=validator,
            tool_gateway=tool_gateway,
            event_log=event_log,
            max_milestone_attempts=5,
            max_plan_attempts=3,
        )

        assert agent.is_full_five_layer_mode
        assert agent._max_milestone_attempts == 5
        assert agent._max_plan_attempts == 3

    def test_implements_orchestration_interface(self) -> None:
        """Agent implements IAgentOrchestration interface."""
        from dare_framework.agent.interfaces import IAgentOrchestration

        model = MockModelAdapter()
        agent = FiveLayerAgent(name="test-agent", model=model)

        # Verify execute method exists with correct signature
        assert hasattr(agent, "execute")
        assert callable(agent.execute)

        # Verify it's structurally compatible with IAgentOrchestration
        # (Python's Protocol uses structural subtyping)
        assert isinstance(agent, IAgentOrchestration)


# =============================================================================
# Tests: Execution
# =============================================================================


class TestFiveLayerAgentExecution:
    """Tests for FiveLayerAgent execution."""

    @pytest.mark.asyncio
    async def test_simple_task_without_tools(self) -> None:
        """Simple task without tool calls returns model response."""
        model = MockModelAdapter([
            ModelResponse(content="The answer is 42.", tool_calls=[])
        ])
        agent = FiveLayerAgent(name="test-agent", model=model)

        result = await agent.run("What is the answer?")

        # Result contains the model response content
        assert "The answer is 42." in str(result)
        assert len(model.generate_calls) == 1

    @pytest.mark.asyncio
    async def test_event_logging(self) -> None:
        """Events are logged when event_log is provided."""
        model = MockModelAdapter()
        event_log = MockEventLog()
        agent = FiveLayerAgent(name="test-agent", model=model, event_log=event_log)

        await agent.run("Test task")

        # Without planner or tools, runs in simple mode
        # Should have simple.start, simple.complete
        event_types = [e[0] for e in event_log.events]
        assert "simple.start" in event_types
        assert "simple.complete" in event_types

    @pytest.mark.asyncio
    async def test_budget_check_called(self) -> None:
        """Budget check is called during execution."""
        model = MockModelAdapter()
        context = MagicMock()
        context.stm_add = MagicMock()
        context.stm_get = MagicMock(return_value=[])
        context.budget_check = MagicMock()
        context.budget_use = MagicMock()
        context.assemble = MagicMock(return_value=MagicMock(
            messages=[],
            tools=[],
            metadata={},
        ))

        agent = FiveLayerAgent(name="test-agent", model=model, context=context)
        await agent.run("Test task")

        # Budget check should be called multiple times
        assert context.budget_check.call_count >= 1


# =============================================================================
# Tests: ReAct Mode (No Planner)
# =============================================================================


class TestReActMode:
    """Tests for ReAct mode (no planner)."""

    @pytest.mark.asyncio
    async def test_react_mode_skips_plan_loop(self) -> None:
        """Without planner but with tools, runs in ReAct mode."""
        model = MockModelAdapter()
        tool_gateway = MockToolGateway()
        agent = FiveLayerAgent(name="react-agent", model=model, tool_gateway=tool_gateway)

        # Should be in react mode
        assert agent.is_react_mode
        assert not agent.is_full_five_layer_mode
        assert not agent.is_simple_mode

        # Should not raise, just execute in ReAct mode
        result = await agent.run("Do something")
        assert result is not None

    @pytest.mark.asyncio
    async def test_react_mode_with_tool_calls(self) -> None:
        """ReAct mode handles tool calls."""
        model = MockModelAdapter([
            ModelResponse(
                content="Let me check...",
                tool_calls=[{"name": "read_file", "arguments": {"path": "/tmp/test"}}],
            ),
            ModelResponse(content="Done!", tool_calls=[]),
        ])
        tool_gateway = MockToolGateway()
        agent = FiveLayerAgent(
            name="react-agent",
            model=model,
            tool_gateway=tool_gateway,
        )

        result = await agent.run("Read a file")

        assert len(tool_gateway.invoke_calls) == 1
        assert tool_gateway.invoke_calls[0][0] == "read_file"


# =============================================================================
# Tests: Full Five-Layer Mode
# =============================================================================


class TestFiveLayerMode:
    """Tests for full five-layer mode."""

    @pytest.mark.asyncio
    async def test_plan_loop_generates_plan(self) -> None:
        """Plan loop generates a plan when planner is provided."""
        model = MockModelAdapter()
        planner = MockPlanner()
        validator = MockValidator()
        agent = FiveLayerAgent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
        )

        await agent.run("Create a plan")

        assert len(planner.plan_calls) >= 1
        assert len(validator.validate_calls) >= 1

    @pytest.mark.asyncio
    async def test_milestone_verification(self) -> None:
        """Milestone verification is called when validator is provided."""
        model = MockModelAdapter()
        planner = MockPlanner()
        validator = MockValidator()
        agent = FiveLayerAgent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
        )

        await agent.run("Complete a milestone")

        assert len(validator.verify_calls) >= 1

    @pytest.mark.asyncio
    async def test_plan_tool_detected_via_registry_metadata(self) -> None:
        """Plan tool detection prefers trusted registry metadata over name prefix."""
        plan_tool = CapabilityDescriptor(
            id="tool:replan",
            type=CapabilityType.TOOL,
            name="replan",
            description="Trigger replanning.",
            input_schema={"type": "object", "properties": {}},
            metadata={"capability_kind": CapabilityKind.PLAN_TOOL},
        )
        model = MockModelAdapter(
            [
                ModelResponse(
                    content="Need to replan.",
                    tool_calls=[{"name": "replan", "arguments": {}}],
                ),
                ModelResponse(content="Done.", tool_calls=[]),
            ]
        )
        planner = MockPlanner()
        validator = MockValidator()
        tool_gateway = MockToolGateway([plan_tool])
        agent = FiveLayerAgent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
            tool_gateway=tool_gateway,
        )

        result = await agent.run("Handle plan tool")

        assert result.success is True
        state = agent._session_state.current_milestone_state
        assert state is not None
        assert any("plan tool encountered" in text for text in state.reflections)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
