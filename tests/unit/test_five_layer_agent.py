"""Unit tests for DareAgent."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from dare_framework.agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Budget, Context, Message
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.plan.types import SessionSummary, Task
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalMatcherKind,
    ApprovalScope,
    JsonApprovalRuleStore,
    ToolApprovalManager,
)
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
        self.decompose_calls = []

    async def plan(self, ctx: Any) -> Any:
        self.plan_calls.append(ctx)
        from dare_framework.plan.types import ProposedPlan
        return ProposedPlan(
            plan_description="Mock plan",
            steps=[],
            attempt=len(self.plan_calls),
        )

    async def decompose(self, task: Task, ctx: Any) -> Any:
        self.decompose_calls.append((task, ctx))
        from dare_framework.plan.types import DecompositionResult, Milestone
        return DecompositionResult(
            milestones=[
                Milestone(
                    milestone_id=f"{task.task_id}_m1",
                    description=task.description,
                    user_input=task.description,
                )
            ],
            reasoning="mock decomposition",
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

    def list_capabilities(self) -> list[Any]:
        return list(self._capabilities)

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> Any:
        self.invoke_calls.append((capability_id, params, envelope))
        return MagicMock(success=True, output={"result": "mock"}, evidence=[])


class MockEventLog:
    """Mock event log for testing."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def append(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))


class MockConfigProvider:
    """Mock config provider for testing."""

    def __init__(self, config: Any) -> None:
        self._config = config

    def current(self) -> Any:
        return self._config

    def reload(self) -> Any:
        return self._config


class RecordingTransportChannel:
    """Transport double that captures outgoing envelopes from direct calls."""

    def __init__(self) -> None:
        self.sent: list[Any] = []

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self) -> Any:
        raise RuntimeError("poll is not used in this test transport")

    async def send(self, msg: Any) -> None:
        self.sent.append(msg)

    def add_action_handler_dispatcher(self, dispatcher: Any) -> None:
        _ = dispatcher

    def add_agent_control_handler(self, handler: Any) -> None:
        _ = handler

    def get_action_handler_dispatcher(self) -> Any:
        return object()

    def get_agent_control_handler(self) -> Any:
        return object()


def _make_agent(*, model: MockModelAdapter, name: str = "test-agent", **kwargs: Any) -> DareAgent:
    """Build DareAgent test instances with an explicit context by default."""
    context = kwargs.pop("context", Context(config=Config()))
    tool_gateway = kwargs.pop("tool_gateway", MockToolGateway())
    return DareAgent(name=name, model=model, context=context, tool_gateway=tool_gateway, **kwargs)


# =============================================================================
# Tests: Initialization
# =============================================================================


class TestDareAgentInit:
    """Tests for DareAgent initialization."""

    def test_init_with_minimal_deps(self) -> None:
        """Agent can be created with only required dependencies."""
        model = MockModelAdapter()
        agent = _make_agent(name="test-agent", model=model)

        assert agent.name == "test-agent"
        assert agent.context is not None
        assert not agent.is_full_five_layer_mode

    def test_init_with_context(self) -> None:
        """Agent can use a provided context."""
        model = MockModelAdapter()
        context = Context(id="custom-context", budget=Budget(max_tokens=1000), config=Config())
        agent = _make_agent(name="test-agent", model=model, context=context)

        assert agent.context.id == "custom-context"

    def test_init_with_planner_enables_five_layer_mode(self) -> None:
        """Providing a planner enables full five-layer mode."""
        model = MockModelAdapter()
        planner = MockPlanner()
        agent = _make_agent(name="test-agent", model=model, planner=planner)

        assert agent.is_full_five_layer_mode

    def test_init_with_all_deps(self) -> None:
        """Agent can be created with all dependencies."""
        model = MockModelAdapter()
        planner = MockPlanner()
        validator = MockValidator()
        tool_gateway = MockToolGateway()
        event_log = MockEventLog()

        agent = _make_agent(
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
        agent = _make_agent(name="test-agent", model=model)

        # Verify execute method exists on orchestration contract.
        assert hasattr(agent, "execute")
        assert callable(agent.execute)

        # Verify it's compatible with IAgentOrchestration (ABC inheritance).
        assert isinstance(agent, IAgentOrchestration)


# =============================================================================
# Tests: Execution
# =============================================================================


class TestDareAgentExecution:
    """Tests for DareAgent execution."""

    @pytest.mark.asyncio
    async def test_simple_task_without_tools(self) -> None:
        """Simple task without tool calls returns model response."""
        model = MockModelAdapter([
            ModelResponse(content="The answer is 42.", tool_calls=[])
        ])
        agent = _make_agent(name="test-agent", model=model)

        result = await agent("What is the answer?")

        # Result contains the model response content
        assert "The answer is 42." in str(result)
        assert len(model.generate_calls) == 1

    @pytest.mark.asyncio
    async def test_run_result_output_text_normalizes_serialized_list_content(self) -> None:
        """RunResult.output_text decodes serialized list-style model content."""
        serialized = "[\"\\u4efb\\u52a1\\u6807\\u9898\\n\", \"print(\\\"ok\\\")\\n\"]"
        model = MockModelAdapter([
            ModelResponse(content=serialized, tool_calls=[])
        ])
        agent = _make_agent(name="test-agent", model=model)

        result = await agent("Generate python file")

        assert isinstance(result.output, dict)
        assert result.output.get("content") == serialized
        assert result.output_text is not None
        assert "任务标题" in result.output_text
        assert 'print("ok")' in result.output_text

    @pytest.mark.asyncio
    async def test_event_logging(self) -> None:
        """Events are logged when event_log is provided."""
        model = MockModelAdapter()
        event_log = MockEventLog()
        agent = _make_agent(name="test-agent", model=model, event_log=event_log)

        await agent("Test task")

        # Runs through session loop even without planner/tools.
        event_types = [e[0] for e in event_log.events]
        assert "session.start" in event_types
        assert "session.complete" in event_types

    @pytest.mark.asyncio
    async def test_budget_check_called(self) -> None:
        """Budget check is called during execution."""
        model = MockModelAdapter()
        context = MagicMock()
        context.stm_add = MagicMock()
        context.stm_get = MagicMock(return_value=[])
        context.budget_check = MagicMock()
        context.budget_use = MagicMock()
        context.budget = Budget()
        context.budget_remaining = MagicMock(return_value=float("inf"))
        context.assemble = MagicMock(return_value=MagicMock(
            messages=[],
            tools=[],
            metadata={},
        ))

        agent = _make_agent(name="test-agent", model=model, context=context)
        await agent("Test task")

        # Budget check should be called multiple times
        assert context.budget_check.call_count >= 1

    @pytest.mark.asyncio
    async def test_no_planner_session_path_does_not_write_debug_output_to_stdout(self, capsys) -> None:
        """No-planner session path should avoid unconditional debug stdout output."""
        model = MockModelAdapter([ModelResponse(content="ok", tool_calls=[])])
        agent = _make_agent(name="test-agent", model=model)

        await agent("quiet task")

        captured = capsys.readouterr()
        assert "[DEBUG]" not in captured.out
        assert "--- [0] user ---" not in captured.out


# =============================================================================
# Tests: No Planner With Tools
# =============================================================================


class TestNoPlannerToolExecution:
    """Tests for no-planner execution path with tools."""

    @pytest.mark.asyncio
    async def test_no_planner_executes_without_plan_loop(self) -> None:
        """Without planner but with tools, execution still succeeds."""
        model = MockModelAdapter()
        tool_gateway = MockToolGateway(
            [
                CapabilityDescriptor(
                    id="read_file",
                    type=CapabilityType.TOOL,
                    name="read_file",
                    description="Read file content.",
                    input_schema={"type": "object"},
                )
            ]
        )
        agent = _make_agent(name="react-agent", model=model, tool_gateway=tool_gateway)

        assert not agent.is_full_five_layer_mode

        result = await agent("Do something")
        assert result is not None

    @pytest.mark.asyncio
    async def test_no_planner_with_tool_calls(self) -> None:
        """No-planner path handles tool calls."""
        model = MockModelAdapter([
            ModelResponse(
                content="Let me check...",
                tool_calls=[{"name": "read_file", "arguments": {"path": "/tmp/test"}}],
            ),
            ModelResponse(content="Done!", tool_calls=[]),
        ])
        tool_gateway = MockToolGateway(
            [
                CapabilityDescriptor(
                    id="read_file",
                    type=CapabilityType.TOOL,
                    name="read_file",
                    description="Read file content.",
                    input_schema={"type": "object"},
                )
            ]
        )
        agent = _make_agent(
            name="react-agent",
            model=model,
            tool_gateway=tool_gateway,
        )

        result = await agent("Read a file")

        assert len(tool_gateway.invoke_calls) == 1
        assert tool_gateway.invoke_calls[0][0] == "read_file"
        messages = agent._context.stm_get()
        assert any(msg.role == "assistant" and msg.metadata.get("tool_calls") for msg in messages)
        assert any(msg.role == "tool" for msg in messages)

    @pytest.mark.asyncio
    async def test_no_planner_requires_approval_then_reuses_workspace_rule(self, tmp_path) -> None:
        capability = CapabilityDescriptor(
            id="run_command",
            type=CapabilityType.TOOL,
            name="run_command",
            description="Run a shell command.",
            input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
            metadata={"requires_approval": True},
        )
        tool_gateway = MockToolGateway([capability])
        approval_manager = ToolApprovalManager(
            workspace_store=JsonApprovalRuleStore(tmp_path / "workspace" / "approvals.json"),
            user_store=JsonApprovalRuleStore(tmp_path / "user" / "approvals.json"),
        )

        first_model = MockModelAdapter(
            [
                ModelResponse(
                    content="Running command...",
                    tool_calls=[{"name": "run_command", "arguments": {"command": "git status --short"}}],
                ),
                ModelResponse(content="Done.", tool_calls=[]),
            ]
        )
        first_agent = _make_agent(
            name="react-agent-approval",
            model=first_model,
            tool_gateway=tool_gateway,
            approval_manager=approval_manager,
        )

        first_run = asyncio.create_task(first_agent("Run git status"))
        pending = []
        for _ in range(100):
            pending = approval_manager.list_pending()
            if pending:
                break
            await asyncio.sleep(0.01)
        assert pending

        request_id = pending[0].request_id
        await approval_manager.grant(
            request_id,
            scope=ApprovalScope.WORKSPACE,
            matcher=ApprovalMatcherKind.EXACT_PARAMS,
        )

        first_result = await first_run
        assert first_result.success is True
        assert len(tool_gateway.invoke_calls) == 1
        assert approval_manager.list_pending() == []

        second_model = MockModelAdapter(
            [
                ModelResponse(
                    content="Running command again...",
                    tool_calls=[{"name": "run_command", "arguments": {"command": "git status --short"}}],
                ),
                ModelResponse(content="Done again.", tool_calls=[]),
            ]
        )
        second_agent = _make_agent(
            name="react-agent-approval-second",
            model=second_model,
            tool_gateway=tool_gateway,
            approval_manager=approval_manager,
        )

        second_result = await second_agent("Run git status again")
        assert second_result.success is True
        assert len(tool_gateway.invoke_calls) == 2
        assert approval_manager.list_pending() == []

    @pytest.mark.asyncio
    async def test_no_planner_emits_transport_approval_pending_message(self, tmp_path) -> None:
        capability = CapabilityDescriptor(
            id="run_command",
            type=CapabilityType.TOOL,
            name="run_command",
            description="Run a shell command.",
            input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
            metadata={"requires_approval": True},
        )
        tool_gateway = MockToolGateway([capability])
        approval_manager = ToolApprovalManager(
            workspace_store=JsonApprovalRuleStore(tmp_path / "workspace" / "approvals.json"),
            user_store=JsonApprovalRuleStore(tmp_path / "user" / "approvals.json"),
        )
        model = MockModelAdapter(
            [
                ModelResponse(
                    content="Running command...",
                    tool_calls=[{"name": "run_command", "arguments": {"command": "git status --short"}}],
                ),
                ModelResponse(content="Done.", tool_calls=[]),
            ]
        )
        agent = _make_agent(
            name="react-agent-approval-transport",
            model=model,
            tool_gateway=tool_gateway,
            approval_manager=approval_manager,
        )
        transport = RecordingTransportChannel()

        run_task = asyncio.create_task(agent("Run git status", transport=transport))
        request_id: str | None = None
        for _ in range(100):
            for envelope in transport.sent:
                payload = getattr(envelope, "payload", None)
                if not isinstance(payload, dict):
                    continue
                if payload.get("type") != "approval_pending":
                    continue
                resp = payload.get("resp")
                if not isinstance(resp, dict):
                    continue
                request = resp.get("request")
                if isinstance(request, dict) and isinstance(request.get("request_id"), str):
                    request_id = request["request_id"]
                    break
            if request_id is not None:
                break
            await asyncio.sleep(0.01)
        assert request_id is not None

        await approval_manager.grant(
            request_id,
            scope=ApprovalScope.ONCE,
            matcher=ApprovalMatcherKind.EXACT_PARAMS,
        )

        result = await run_task
        assert result.success is True


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
        agent = _make_agent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
        )

        await agent("Create a plan")

        assert len(planner.plan_calls) >= 1
        assert len(validator.validate_calls) >= 1

    @pytest.mark.asyncio
    async def test_milestone_verification(self) -> None:
        """Milestone verification is called when validator is provided."""
        model = MockModelAdapter()
        planner = MockPlanner()
        validator = MockValidator()
        agent = _make_agent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
        )

        await agent("Complete a milestone")

        assert len(validator.verify_calls) >= 1

    @pytest.mark.asyncio
    async def test_plan_tool_detected_via_registry_metadata(self) -> None:
        """Plan tool detection prefers trusted registry metadata over name prefix."""
        plan_tool = CapabilityDescriptor(
            id="replan",
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
        agent = _make_agent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
            tool_gateway=tool_gateway,
        )

        result = await agent("Handle plan tool")

        assert result.success is True
        state = agent._session_state.current_milestone_state
        assert state is not None
        assert any("plan tool encountered" in text for text in state.reflections)

    @pytest.mark.asyncio
    async def test_run_result_fields_for_session_loop(self) -> None:
        """Session loop returns success/output/errors in RunResult."""
        model = MockModelAdapter()
        planner = MockPlanner()
        validator = MockValidator()
        agent = _make_agent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
        )

        result = await agent("Summarize this run")

        assert result.success is True
        assert result.errors == []
        assert result.output is not None

    @pytest.mark.asyncio
    async def test_previous_session_summary_not_auto_injected(self) -> None:
        """Current implementation keeps previous_session_summary on Task only."""
        model = MockModelAdapter()
        planner = MockPlanner()
        validator = MockValidator()
        agent = _make_agent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
        )

        previous_summary = SessionSummary(
            session_id="session_prev",
            task_id="task_prev",
            success=True,
            started_at=0.0,
            ended_at=1.0,
            duration_ms=1000.0,
            milestones=[],
            final_output=None,
            errors=[],
            metadata={},
        )

        await agent(
            Task(
                description="Follow-up task",
                previous_session_summary=previous_summary,
            )
        )

        messages = agent._context.stm_get()
        assert messages[0].role == "user"
        assert "Follow-up task" in (messages[0].content or "")

    @pytest.mark.asyncio
    async def test_session_start_includes_task_and_run_ids(self) -> None:
        """session.start event includes task/run identifiers."""
        model = MockModelAdapter()
        planner = MockPlanner()
        validator = MockValidator()
        event_log = MockEventLog()
        agent = _make_agent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
            event_log=event_log,
        )

        await agent("Task with config")

        session_start = [e for e in event_log.events if e[0] == "session.start"]
        assert session_start
        assert session_start[0][1].get("task_id")
        assert session_start[0][1].get("run_id")

    @pytest.mark.asyncio
    async def test_milestone_attempt_count_is_persisted_on_state(self) -> None:
        """MilestoneState.attempts should reflect actual retry count."""
        model = MockModelAdapter([ModelResponse(content="still failing", tool_calls=[])])
        planner = MockPlanner()
        validator = MockValidator(verify_success=False)
        agent = _make_agent(
            name="five-layer-agent",
            model=model,
            planner=planner,
            validator=validator,
            max_milestone_attempts=2,
        )

        result = await agent("Task that fails verification")

        assert result.success is False
        state = agent._session_state.current_milestone_state
        assert state is not None
        assert state.attempts == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
