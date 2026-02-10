"""DareAgent - DARE Framework agent implementation.

This agent implements the full five-layer orchestration loop:
1. Session Loop - Top-level task lifecycle
2. Milestone Loop - Sub-goal tracking and verification
3. Plan Loop - Plan generation and validation
4. Execute Loop - Model-driven execution
5. Tool Loop - Individual tool invocations

All Plan components (planner, validator, remediator) are optional;
when not provided, the agent degrades gracefully to a ReAct-style loop.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from dare_framework.agent._internal.orchestration import MilestoneState, SessionState
from dare_framework.agent.base_agent import BaseAgent
from dare_framework.config import Config
from dare_framework.context import AssembledContext, Context, Message
from dare_framework.hook._internal.hook_extension_point import HookExtensionPoint
from dare_framework.hook.types import HookPhase
from dare_framework.model import IModelAdapter, ModelInput
from dare_framework.observability._internal.event_trace_bridge import make_trace_aware
from dare_framework.observability._internal.otel_provider import (
    NoOpTelemetryProvider,
    OTelTelemetryProvider,
)
from dare_framework.observability._internal.tracing_hook import ObservabilityHook
from dare_framework.plan.interfaces import (
    IEvidenceCollector,
    IPlanAttemptSandbox,
    IStepExecutor,
)
from dare_framework.plan.types import (
    DonePredicate,
    Envelope,
    Milestone,
    RunResult,
    Task,
    ToolLoopRequest,
    ValidatedPlan,
    VerifyResult,
)
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalEvaluationStatus,
)
from dare_framework.tool.types import CapabilityKind
from dare_framework.transport.types import TransportEnvelope, new_envelope_id


@dataclass
class MilestoneResult:
    """Result from a milestone loop execution."""
    success: bool
    outputs: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    verify_result: VerifyResult | None = None


if TYPE_CHECKING:
    from dare_framework.context import Budget
    from dare_framework.context.kernel import IContext
    from dare_framework.event.kernel import IEventLog
    from dare_framework.hook.kernel import IHook
    from dare_framework.observability.kernel import ITelemetryProvider
    from dare_framework.memory import ILongTermMemory, IShortTermMemory
    from dare_framework.plan.interfaces import IPlanner, IRemediator, IValidator
    from dare_framework.tool.interfaces import IExecutionControl
    from dare_framework.tool.kernel import IToolGateway
    from dare_framework.tool._internal.control.approval_manager import ToolApprovalManager
    from dare_framework.transport.kernel import AgentChannel


class DareAgent(BaseAgent):
    """DARE Framework agent implementation.

    This agent implements the IAgentOrchestration interface and supports
    the full five-layer orchestration loop while allowing graceful
    degradation when optional components are not provided.

    Architecture:
        - Implements IAgentOrchestration.run_task() as the core entry point
        - Overrides BaseAgent.run() to delegate to run_task()
        - Preserves _execute() for BaseAgent compatibility

    Modes:
        - **Full Five-Layer**: planner provided → Session→Milestone→Plan→Execute→Tool
        - **ReAct Mode**: no planner, has tools → Execute→Tool loop directly
        - **Simple Mode**: no planner, no tools → Single model generation

    Example:
        # Full five-layer mode
        agent = DareAgent(
            name="full-agent",
            model=model,
            planner=planner,
            validator=validator,
        )

        # ReAct mode (no planner/validator)
        agent = DareAgent(
            name="react-agent",
            model=model,
            tool_gateway=gateway,
        )
    """

    def __init__(
        self,
        name: str,
        *,
        model: IModelAdapter,
        context: IContext | None = None,
        # Memory components (optional)
        short_term_memory: IShortTermMemory | None = None,
        long_term_memory: ILongTermMemory | None = None,
        # Tool components (optional)
        tool_gateway: IToolGateway | None = None,
        execution_control: IExecutionControl | None = None,
        approval_manager: ToolApprovalManager | None = None,
        # Plan components (optional - enables full five-layer mode)
        planner: IPlanner | None = None,
        validator: IValidator | None = None,
        remediator: IRemediator | None = None,
        # Observability components (optional)
        event_log: IEventLog | None = None,
        hooks: list[IHook] | None = None,
        telemetry: ITelemetryProvider | None = None,
        # Milestone orchestration components (optional)
        sandbox: IPlanAttemptSandbox | None = None,
        step_executor: IStepExecutor | None = None,
        evidence_collector: IEvidenceCollector | None = None,
        # Configuration
        budget: Budget | None = None,
        execution_mode: str = "model_driven",  # "model_driven" or "step_driven"
        max_milestone_attempts: int = 3,
        max_plan_attempts: int = 3,
        max_tool_iterations: int = 20,
        verbose: bool = False,
        agent_channel: AgentChannel | None = None,
    ) -> None:
        """Initialize DareAgent.

        Args:
            name: Agent name identifier.
            model: Model adapter for generating responses (required).
            context: Pre-configured context (optional).
            short_term_memory: Short-term memory (optional).
            long_term_memory: Long-term memory (optional).
            tools: Tool provider for listing tools (optional).
            tool_gateway: Tool gateway for invoking tools (optional).
            execution_control: Execution control for HITL (optional).
            approval_manager: Tool approval manager for persisted approval memory (optional).
            planner: Plan generator (optional, enables full five-layer).
            validator: Plan/milestone validator (optional).
            remediator: Failure remediator (optional).
            event_log: Event log for audit (optional).
            hooks: Hook implementations invoked at lifecycle phases (optional).
            telemetry: Telemetry provider for traces/metrics/logs (optional).
            budget: Resource budget (optional).
            max_milestone_attempts: Max retries per milestone.
            max_plan_attempts: Max plan generation attempts.
            max_tool_iterations: Max tool call iterations per execute loop.
            sandbox: Plan attempt sandbox for state isolation (optional).
            step_executor: Step executor for step-driven mode (optional).
            evidence_collector: Evidence collector for verification (optional).
            execution_mode: "model_driven" (default) or "step_driven".
        """
        super().__init__(name, agent_channel=agent_channel)
        self._model = model
        self._logger = logging.getLogger("dare.agent")

        # Create or use provided context
        if context is None:
            from dare_framework.context import Budget as BudgetClass

            self._context = Context(
                id=f"context_{name}",
                short_term_memory=short_term_memory,
                long_term_memory=long_term_memory,
                budget=budget or BudgetClass(),
                config=Config(),
            )
        else:
            self._context = context

        # Tool components
        self._tool_gateway = tool_gateway
        self._exec_ctl = execution_control
        self._approval_manager = approval_manager

        # Plan components (optional)
        self._planner = planner
        self._validator = validator
        self._remediator = remediator

        # Milestone orchestration components (optional)
        self._sandbox = sandbox
        self._step_executor = step_executor
        self._evidence_collector = evidence_collector
        self._execution_mode = execution_mode

        # Create default sandbox if not provided
        if self._sandbox is None:
            from dare_framework.agent._internal.sandbox import DefaultPlanAttemptSandbox
            self._sandbox = DefaultPlanAttemptSandbox()

        # Observability
        self._telemetry = telemetry if telemetry is not None else NoOpTelemetryProvider()
        self._event_log = make_trace_aware(event_log)
        self._hooks = list(hooks) if hooks is not None else []
        if isinstance(self._telemetry, OTelTelemetryProvider):
            if not any(isinstance(hook, ObservabilityHook) for hook in self._hooks):
                self._hooks.append(ObservabilityHook(self._telemetry))
        self._extension_point = HookExtensionPoint(self._hooks) if self._hooks else None

        # Configuration
        self._max_milestone_attempts = max_milestone_attempts
        self._max_plan_attempts = max_plan_attempts
        self._max_tool_iterations = max_tool_iterations
        self._verbose = verbose


        # Runtime state (set during execution)
        self._session_state: SessionState | None = None
        self._token_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}

    @property
    def context(self) -> IContext:
        """Agent context."""
        return self._context

    @property
    def is_full_five_layer_mode(self) -> bool:
        """Check if agent has full five-layer capabilities."""
        return self._planner is not None

    @property
    def is_react_mode(self) -> bool:
        """Check if agent should run in ReAct mode.

        ReAct mode: No planner, but has tool_gateway.
        Skips Session/Milestone loops, runs Execute+Tool directly.
        """
        return self._planner is None and self._tool_gateway is not None

    @property
    def is_simple_mode(self) -> bool:
        """Check if agent should run in simple chat mode.

        Simple mode: No planner and no tool_gateway.
        Just model generation, no tools.
        """
        return self._planner is None and self._tool_gateway is None

    def _log(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self._verbose:
            print(f"[DareAgent] {message}")

    # =========================================================================
    # IAgentOrchestration Implementation
    # =========================================================================

    async def run_task(
        self,
        task: Task,
        deps: Any | None = None,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Execute a task with automatic mode selection.

        This is the primary entry point implementing IAgentOrchestration.
        Mode is automatically selected based on component configuration:

        - **Full Five-Layer**: planner is provided → Session→Milestone→Plan→Execute→Tool
        - **ReAct Mode**: no planner, has tools → Execute→Tool loop directly
        - **Simple Mode**: no planner, no tools → Single model generation

        Args:
            task: Task to execute.
            deps: Optional dependencies (unused, for interface compatibility).
            transport: Optional transport channel for streaming outputs.

        Returns:
            RunResult for single-task execution.
        """
        previous = self._active_transport
        self._active_transport = transport
        try:
            start_time = time.perf_counter()
            # Task is frozen; create a new instance with task_id if missing
            if task.task_id is None:
                task = replace(task, task_id=uuid4().hex[:8])
            self._session_state = SessionState(task_id=task.task_id)
            self._token_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
            if self.is_full_five_layer_mode or task.milestones:
                execution_mode = "full_five_layer"
            elif self.is_react_mode:
                execution_mode = "react"
            else:
                execution_mode = "simple"
            await self._emit_hook(
                HookPhase.BEFORE_RUN,
                {
                    "task_id": self._session_state.task_id,
                    "session_id": self._session_state.run_id,
                    "agent_name": self.name,
                    "execution_mode": execution_mode,
                },
            )
            result: RunResult | None = None
            error: Exception | None = None

            try:
                # Full five-layer mode: has planner or task has explicit milestones
                if self.is_full_five_layer_mode or task.milestones:
                    result = await self._run_session_loop(task)
                # ReAct mode: no planner but has tools
                elif self.is_react_mode:
                    result = await self._run_react_loop(task)
                # Simple mode: no planner, no tools → just model generation
                else:
                    result = await self._run_simple_loop(task)
                return result
            except Exception as exc:
                error = exc
                raise
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                errors: list[str] = []
                if result is not None and result.errors:
                    errors.extend([str(item) for item in result.errors])
                if error is not None:
                    errors.append(str(error))
                token_usage = {
                    "input_tokens": self._token_usage.get("input_tokens", 0),
                    "output_tokens": self._token_usage.get("output_tokens", 0),
                    "total_tokens": self._token_usage.get("input_tokens", 0)
                    + self._token_usage.get("output_tokens", 0),
                    "cached_tokens": self._token_usage.get("cached_tokens", 0),
                }
                payload = {
                    "success": result.success if result is not None else False,
                    "token_usage": token_usage,
                    "errors": errors,
                    "duration_ms": duration_ms,
                    "budget_stats": self._budget_stats(),
                }
                await self._emit_hook(HookPhase.AFTER_RUN, payload)
        finally:
            self._active_transport = previous

    # =========================================================================
    # IAgent.run() Override
    # =========================================================================

    async def run(
        self,
        task: str | Task,
        deps: Any | None = None,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Run a task and return a structured RunResult.

        Overrides BaseAgent.run() to delegate to run_task().

        Args:
            task: Task description string or Task object.
            deps: Optional dependencies.
            transport: Optional transport channel for streaming outputs.

        Returns:
            RunResult with execution outcome.
        """
        if isinstance(task, Task):
            task_obj = task
        else:
            task_obj = Task(
                description=task,
                task_id=uuid4().hex[:8],
            )
        result = await self.run_task(task_obj, deps, transport=transport)
        await self._send_transport_result(result, task=task_obj.description, transport=transport)
        return result

    # =========================================================================
    # BaseAgent Compatibility
    # =========================================================================

    async def _execute(self, task: str) -> str:
        """Execute task - BaseAgent compatibility layer.

        This method is preserved for compatibility with BaseAgent.
        Internally delegates to run_task() and converts result to string.
        """
        result = await self.run(task)
        if result.output is not None:
            return str(result.output)
        if result.errors:
            return f"Error: {'; '.join(result.errors)}"
        return ""

    # =========================================================================
    # ReAct Loop (Degraded Mode - No Session/Milestone)
    # =========================================================================

    async def _run_react_loop(self, task: Task) -> RunResult:
        """Run ReAct-style loop - direct Execute+Tool without Session/Milestone.

        This is the degraded mode when no planner is configured but tools are
        available. Skips Session and Milestone loops, runs Execute→Tool directly.
        """
        await self._log_event("react.start", {
            "task_description": task.description[:100],
        })

        # Add user message to STM
        user_message = Message(role="user", content=task.description)
        self._context.stm_add(user_message)

        # Run execute loop directly (no plan, no milestone)
        execute_result = await self._run_execute_loop(None)

        await self._log_event("react.complete", {
            "success": execute_result.get("success", False),
        })

        return RunResult(
            success=execute_result.get("success", False),
            output=execute_result.get("outputs", [])[-1] if execute_result.get("outputs") else None,
            errors=execute_result.get("errors", []),
        )

    # =========================================================================
    # Simple Loop (Degraded Mode - No Tools)
    # =========================================================================

    async def _run_simple_loop(self, task: Task) -> RunResult:
        """Run simple loop - single model generation without tools.

        This is the most degraded mode when neither planner nor tools are
        configured. Just generates a single model response.
        """
        await self._log_event("simple.start", {
            "task_description": task.description[:100],
        })
        execute_start = time.perf_counter()
        await self._emit_hook(HookPhase.BEFORE_EXECUTE, {"mode": "simple"})

        # Add user message to STM
        user_message = Message(role="user", content=task.description)
        self._context.stm_add(user_message)

        # Budget check
        self._context.budget_check()

        # Assemble context
        await self._emit_hook(HookPhase.BEFORE_CONTEXT_ASSEMBLE, {})
        assembled = self._context.assemble()
        assembled_messages = self._assemble_messages(assembled)
        await self._emit_hook(
            HookPhase.AFTER_CONTEXT_ASSEMBLE,
            {
                **self._context_stats(assembled_messages, len(assembled.tools)),
                "budget_stats": self._budget_stats(),
            },
        )

        # Create model input
        model_input = ModelInput(
            messages=assembled_messages,
            tools=[],  # No tools in simple mode
            metadata=assembled.metadata,
        )

        # Generate model response
        for idx, m in enumerate(model_input.messages):
            print(f"\n--- [{idx}] {m.role} ---\n{m.content}\n", flush=True)
        await self._emit_hook(HookPhase.BEFORE_MODEL, {
            "model_name": getattr(self._model, "name", None),
        })
        model_start = time.perf_counter()
        response = await self._model.generate(model_input)
        model_latency_ms = (time.perf_counter() - model_start) * 1000.0

        # Add response to STM
        assistant_message = Message(role="assistant", content=response.content)
        self._context.stm_add(assistant_message)

        # Record token usage
        if response.usage:
            self._record_token_usage(response.usage)
            total_tokens = self._total_tokens_from_usage(response.usage)
            if total_tokens:
                self._context.budget_use("tokens", total_tokens)

        await self._emit_hook(HookPhase.AFTER_MODEL, {
            "model_usage": response.usage or {},
            "duration_ms": model_latency_ms,
            "budget_stats": self._budget_stats(),
        })

        await self._log_event("simple.complete", {
            "success": True,
        })
        await self._emit_hook(HookPhase.AFTER_EXECUTE, {
            "success": True,
            "duration_ms": (time.perf_counter() - execute_start) * 1000.0,
            "budget_stats": self._budget_stats(),
        })

        return RunResult(
            success=True,
            output={"content": response.content},
            errors=[],
        )

    # =========================================================================
    # Session Loop (Layer 1)
    # =========================================================================

    async def _run_session_loop(self, task: Task) -> RunResult:
        """Run the session loop - top-level task lifecycle."""
        # Initialize session state
        if self._session_state is None:
            self._session_state = SessionState(
                task_id=task.task_id or uuid4().hex[:8],
            )
        session_start = time.perf_counter()
        await self._emit_hook(HookPhase.BEFORE_SESSION, {
            "task_id": self._session_state.task_id,
            "run_id": self._session_state.run_id,
        })

        # Log session start
        await self._log_event("session.start", {
            "task_id": self._session_state.task_id,
            "run_id": self._session_state.run_id,
        })

        # Add user message to STM
        user_message = Message(role="user", content=task.description)
        self._context.stm_add(user_message)

        # Get or decompose milestones
        if task.milestones:
            # Use pre-defined milestones
            milestones = list(task.milestones)
            await self._log_event("session.milestones_predefined", {
                "count": len(milestones),
            })
        elif self._planner is not None:
            # Decompose task into milestones using planner
            self._log("Decomposing task into milestones...")
            decomposition = await self._planner.decompose(task, self._context)
            milestones = decomposition.milestones
            await self._log_event("session.milestones_decomposed", {
                "count": len(milestones),
                "reasoning": decomposition.reasoning,
            })
        else:
            # Fall back to single milestone
            milestones = task.to_milestones()
            await self._log_event("session.milestones_default", {
                "count": len(milestones),
            })

        # Initialize milestone states
        for milestone in milestones:
            self._session_state.milestone_states.append(
                MilestoneState(milestone=milestone)
            )

        # Run milestone loop for each milestone
        milestone_results = []
        errors: list[str] = []

        for idx, milestone in enumerate(milestones):
            self._session_state.current_milestone_idx = idx
            print(f"[DEBUG] Starting milestone {idx + 1}/{len(milestones)}: {milestone.milestone_id}", flush=True)

            # Check budget before each milestone
            # TODO(@mahaichuan-qq): Confirm exception type for budget_check()
            self._context.budget_check()

            # Check execution control
            # TODO(@bouillipx): Confirm poll_or_raise() exists
            if self._exec_ctl is not None:
                self._poll_or_raise()

            result = await self._run_milestone_loop(milestone)
            milestone_results.append(result)
            print(f"[DEBUG] Milestone {idx + 1} result: success={result.success}", flush=True)

            if not result.success:
                errors.extend(result.errors or ["milestone failed"])
                break

        # Log session complete
        success = not errors
        await self._log_event("session.complete", {
            "task_id": self._session_state.task_id,
            "run_id": self._session_state.run_id,
            "success": success,
        })
        await self._emit_hook(HookPhase.AFTER_SESSION, {
            "success": success,
            "duration_ms": (time.perf_counter() - session_start) * 1000.0,
            "budget_stats": self._budget_stats(),
        })

        # Get output from last milestone
        output = None
        if milestone_results:
            last_result = milestone_results[-1]
            if last_result.outputs:
                output = last_result.outputs[-1]

        return RunResult(
            success=success,
            output=output,
            errors=errors,
        )

    # =========================================================================
    # Milestone Loop (Layer 2)
    # =========================================================================

    async def _run_milestone_loop(self, milestone: Milestone) -> MilestoneResult:
        """Run the milestone loop - sub-goal tracking."""
        milestone_start = time.perf_counter()
        await self._emit_hook(HookPhase.BEFORE_MILESTONE, {
            "milestone_id": milestone.milestone_id,
            "milestone_index": self._session_state.current_milestone_idx if self._session_state else None,
        })
        await self._log_event("milestone.start", {
            "milestone_id": milestone.milestone_id,
        })

        milestone_state = self._session_state.current_milestone_state

        for attempt in range(self._max_milestone_attempts):
            print(f"[DEBUG] Milestone attempt {attempt + 1}/{self._max_milestone_attempts}", flush=True)
            # Budget check
            self._context.budget_check()

            # Create snapshot for plan attempt isolation
            snapshot_id = None
            if self._sandbox is not None:
                snapshot_id = self._sandbox.create_snapshot(self._context)
                print(f"[DEBUG] Created STM snapshot: {snapshot_id}", flush=True)

            # Run plan loop (if planner available)
            print("[DEBUG] Running plan loop...", flush=True)
            validated_plan = await self._run_plan_loop(milestone)
            print(f"[DEBUG] Plan loop done, validated_plan={validated_plan is not None}", flush=True)

            # Run execute loop
            print("[DEBUG] Running execute loop...", flush=True)
            execute_result = await self._run_execute_loop(validated_plan)
            print(f"[DEBUG] Execute loop done, result keys={list(execute_result.keys())}", flush=True)

            # Handle plan tool encountered
            if execute_result.get("encountered_plan_tool", False):
                if milestone_state:
                    milestone_state.add_reflection(
                        f"plan tool encountered: {execute_result.get('plan_tool_name')}"
                    )
                # Rollback on plan tool encounter
                if self._sandbox is not None and snapshot_id:
                    self._sandbox.rollback(self._context, snapshot_id)
                    self._log(f"Rolled back STM snapshot: {snapshot_id}")
                continue

            # Verify milestone (if validator available); pass plan so validator can use step criteria (e.g. expected_files)
            verify_result = await self._verify_milestone(execute_result, validated_plan)

            if verify_result.success:
                # Commit snapshot on success (discard, keep current state)
                if self._sandbox is not None and snapshot_id:
                    self._sandbox.commit(snapshot_id)
                    self._log(f"Committed STM snapshot: {snapshot_id}")

                await self._log_event("milestone.success", {
                    "milestone_id": milestone.milestone_id,
                    "attempts": attempt + 1,
                })
                await self._emit_hook(HookPhase.AFTER_MILESTONE, {
                    "milestone_id": milestone.milestone_id,
                    "success": True,
                    "attempts": attempt + 1,
                    "duration_ms": (time.perf_counter() - milestone_start) * 1000.0,
                    "budget_stats": self._budget_stats(),
                })
                return MilestoneResult(
                    success=True,
                    outputs=execute_result.get("outputs", []),
                    errors=[],
                    verify_result=verify_result,
                )

            # Rollback on verification failure
            if self._sandbox is not None and snapshot_id:
                self._sandbox.rollback(self._context, snapshot_id)
                self._log(f"Rolled back STM snapshot: {snapshot_id}")

            # Remediate if available (reflection survives rollback)
            if self._remediator is not None and milestone_state:
                reflection = await self._remediator.remediate(
                    verify_result,
                    ctx=self._context,
                )
                milestone_state.add_reflection(reflection)

        # All attempts exhausted
        await self._log_event("milestone.failed", {
            "milestone_id": milestone.milestone_id,
        })
        await self._emit_hook(HookPhase.AFTER_MILESTONE, {
            "milestone_id": milestone.milestone_id,
            "success": False,
            "attempts": self._max_milestone_attempts,
            "duration_ms": (time.perf_counter() - milestone_start) * 1000.0,
            "budget_stats": self._budget_stats(),
        })
        return MilestoneResult(
            success=False,
            outputs=[],
            errors=["milestone failed after max attempts"],
            verify_result=None,
        )

    # =========================================================================
    # Plan Loop (Layer 3)
    # =========================================================================

    async def _run_plan_loop(self, milestone: Milestone) -> ValidatedPlan | None:
        """Run the plan loop - plan generation and validation.

        Returns None if no planner is configured (ReAct mode).
        """
        if self._planner is None:
            return None  # Skip to execute loop (ReAct mode)

        # Budget check
        self._context.budget_check()

        for attempt in range(self._max_plan_attempts):
            plan_start = time.perf_counter()
            await self._emit_hook(HookPhase.BEFORE_PLAN, {
                "milestone_id": milestone.milestone_id,
                "attempt": attempt + 1,
            })

            # Assemble context for planning
            await self._emit_hook(HookPhase.BEFORE_CONTEXT_ASSEMBLE, {})
            assembled = self._context.assemble()
            assembled_messages = self._assemble_messages(assembled)
            await self._emit_hook(
                HookPhase.AFTER_CONTEXT_ASSEMBLE,
                {
                    **self._context_stats(assembled_messages, len(assembled.tools)),
                    "budget_stats": self._budget_stats(),
                },
            )

            # Generate plan
            proposed = await self._planner.plan(self._context)

            await self._log_event("plan.attempt", {
                "milestone_id": milestone.milestone_id,
                "attempt": attempt + 1,
            })

            # Validate plan (if validator available)
            if self._validator is None:
                # No validator: treat proposed as validated
                await self._emit_hook(HookPhase.AFTER_PLAN, {
                    "milestone_id": milestone.milestone_id,
                    "attempt": attempt + 1,
                    "valid": True,
                    "success": True,
                    "duration_ms": (time.perf_counter() - plan_start) * 1000.0,
                    "budget_stats": self._budget_stats(),
                })
                return ValidatedPlan(
                    success=True,
                    plan_description=proposed.plan_description,
                    steps=[],  # TODO: Convert proposed steps
                )

            validated = await self._validator.validate_plan(proposed, self._context)

            if validated.success:
                await self._log_event("plan.validated", {
                    "milestone_id": milestone.milestone_id,
                })
                await self._emit_hook(HookPhase.AFTER_PLAN, {
                    "milestone_id": milestone.milestone_id,
                    "attempt": attempt + 1,
                    "valid": True,
                    "success": True,
                    "duration_ms": (time.perf_counter() - plan_start) * 1000.0,
                    "budget_stats": self._budget_stats(),
                })
                return validated

            # Plan failed validation
            await self._log_event("plan.invalid", {
                "milestone_id": milestone.milestone_id,
                "errors": validated.errors,
            })
            await self._emit_hook(HookPhase.AFTER_PLAN, {
                "milestone_id": milestone.milestone_id,
                "attempt": attempt + 1,
                "valid": False,
                "success": False,
                "errors": list(validated.errors),
                "duration_ms": (time.perf_counter() - plan_start) * 1000.0,
                "budget_stats": self._budget_stats(),
            })

            milestone_state = self._session_state.current_milestone_state
            if milestone_state:
                milestone_state.add_attempt({
                    "attempt": attempt + 1,
                    "errors": list(validated.errors),
                })

        # All plan attempts exhausted
        return ValidatedPlan(
            success=False,
            plan_description="",
            steps=[],
            errors=["max plan attempts exhausted"],
        )

    # =========================================================================
    # Execute Loop (Layer 4)
    # =========================================================================

    async def _run_execute_loop(self, plan: ValidatedPlan | None) -> dict[str, Any]:
        """Run the execute loop - model-driven execution."""
        self._log("Starting execute loop")
        execute_start = time.perf_counter()
        await self._emit_hook(HookPhase.BEFORE_EXECUTE, {
            "plan_present": plan is not None,
        })
        # Budget check
        self._context.budget_check()

        # Assemble context for execution
        await self._emit_hook(HookPhase.BEFORE_CONTEXT_ASSEMBLE, {})
        assembled = self._context.assemble()
        assembled_messages = self._assemble_messages(assembled)
        await self._emit_hook(
            HookPhase.AFTER_CONTEXT_ASSEMBLE,
            {
                **self._context_stats(assembled_messages, len(assembled.tools)),
                "budget_stats": self._budget_stats(),
            },
        )

        # Create prompt
        model_input = ModelInput(
            messages=assembled_messages,
            tools=assembled.tools,
            metadata=assembled.metadata,
        )

        outputs: list[Any] = []
        errors: list[str] = []

        for iteration in range(self._max_tool_iterations):
            # Budget check each iteration
            self._context.budget_check()

            # Check execution control
            if self._exec_ctl is not None:
                self._poll_or_raise()

            # Generate model response
            self._log(f"Execute iteration {iteration + 1}/{self._max_tool_iterations}")
            for idx, m in enumerate(model_input.messages):
                print(f"\n--- [{idx}] {m.role} ---\n{m.content}\n", flush=True)
            await self._emit_hook(HookPhase.BEFORE_MODEL, {
                "iteration": iteration + 1,
                "model_name": getattr(self._model, "name", None),
            })
            model_start = time.perf_counter()
            response = await self._model.generate(model_input)
            model_latency_ms = (time.perf_counter() - model_start) * 1000.0

            if response.usage:
                self._record_token_usage(response.usage)
                total_tokens = self._total_tokens_from_usage(response.usage)
                if total_tokens:
                    self._context.budget_use("tokens", total_tokens)

            # Log model response
            if response.content:
                content_preview = response.content[:200] + "..." if len(response.content) > 200 else response.content
                self._log(f"LLM Response: {content_preview}")
            self._log(f"Tool calls: {len(response.tool_calls)}")

            await self._log_event("model.response", {
                "iteration": iteration + 1,
                "has_tool_calls": bool(response.tool_calls),
            })
            await self._emit_hook(HookPhase.AFTER_MODEL, {
                "iteration": iteration + 1,
                "has_tool_calls": bool(response.tool_calls),
                "model_usage": response.usage or {},
                "duration_ms": model_latency_ms,
                "budget_stats": self._budget_stats(),
            })

            # No tool calls: we're done
            if not response.tool_calls:
                # Add response to STM
                assistant_message = Message(role="assistant", content=response.content)
                self._context.stm_add(assistant_message)

                outputs.append({"content": response.content})
                return await self._finalize_execute(execute_start, {
                    "success": True,
                    "outputs": outputs,
                    "errors": errors,
                })

            # Process tool calls
            capability_index = await self._capability_index() if response.tool_calls else {}

            # Add assistant message with tool_calls to STM (so LLM can see what it called)
            import json
            assistant_msg = Message(
                role="assistant",
                content=response.content or "",
                metadata={"tool_calls": response.tool_calls} if response.tool_calls else {},
            )
            self._context.stm_add(assistant_msg)

            for tool_call in response.tool_calls:
                name = tool_call.get("name") or ""
                capability_id = tool_call.get("capability_id") or name
                tool_call_id = tool_call.get("id") or f"{capability_id}_{iteration + 1}_{uuid4().hex[:6]}"
                descriptor = capability_index.get(capability_id) or capability_index.get(name)

                # Check for plan tool (registry kind preferred, prefix supported)
                if self._is_plan_tool_call(name, descriptor):
                    return await self._finalize_execute(execute_start, {
                        "success": False,
                        "outputs": outputs,
                        "errors": errors,
                        "encountered_plan_tool": True,
                        "plan_tool_name": name,
                    })

                # Run tool loop
                # Get actual tool name for logging (not internal ID)
                tool_name = name or capability_id
                args = tool_call.get('arguments', {})
                # Log tool call with readable format
                if 'path' in args:
                    self._log(f"🔧 Calling [{tool_name}] path={args.get('path')}")
                elif 'command' in args:
                    self._log(f"🔧 Calling [{tool_name}] command={args.get('command', '')[:50]}")
                elif 'query' in args:
                    self._log(f"🔧 Calling [{tool_name}] query={args.get('query', '')[:50]}")
                else:
                    self._log(f"🔧 Calling [{tool_name}] params={list(args.keys())}")

                tool_result = await self._run_tool_loop(
                    ToolLoopRequest(
                        capability_id=capability_id,
                        params=tool_call.get("arguments", {}),
                    ),
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    descriptor=descriptor,
                )

                # Log result
                result_success = tool_result.get("success", False)
                result_output = tool_result.get("output", {})
                result_error = tool_result.get("error", "")

                if result_success and self._is_skill_tool_call(descriptor):
                    self._mount_skill_from_result(result_output)
                
                if result_success:
                    self._log(f"   ✅ Success: {result_output}")
                else:
                    self._log(f"   ❌ Failed: {result_error}")

                # Add tool result as message to STM (CRITICAL: LLM needs to see result!)
                tool_result_content = json.dumps({
                    "success": result_success,
                    "output": result_output,
                    "error": result_error,
                }) if not result_success else json.dumps({
                    "success": True,
                    "output": result_output,
                })
                tool_msg = Message(
                    role="tool",
                    name=tool_call_id or capability_id,  # Use tool_call_id for OpenAI API format
                    content=tool_result_content,
                )
                self._context.stm_add(tool_msg)

                outputs.append(tool_result)

                if not result_success:
                    errors.append(result_error or "tool failed")

            # Reassemble context with new messages for next iteration
            await self._emit_hook(HookPhase.BEFORE_CONTEXT_ASSEMBLE, {})
            assembled = self._context.assemble()
            assembled_messages = self._assemble_messages(assembled)
            await self._emit_hook(
                HookPhase.AFTER_CONTEXT_ASSEMBLE,
                {
                    **self._context_stats(assembled_messages, len(assembled.tools)),
                    "budget_stats": self._budget_stats(),
                },
            )
            model_input = ModelInput(
                messages=assembled_messages,
                tools=assembled.tools,
                metadata=assembled.metadata,
            )

        # Max iterations reached
        errors.append("max tool iterations reached")
        return await self._finalize_execute(execute_start, {
            "success": False,
            "outputs": outputs,
            "errors": errors,
        })

    # =========================================================================
    # Tool Loop (Layer 5)
    # =========================================================================

    async def _run_tool_loop(
        self,
        request: ToolLoopRequest,
        *,
        tool_name: str,
        tool_call_id: str,
        descriptor: Any | None = None,
    ) -> dict[str, Any]:
        """Run the tool loop - single tool invocation."""
        # Budget check
        self._context.budget_check()

        # Check if tool gateway is available
        if self._tool_gateway is None:
            return {
                "success": False,
                "error": "no tool gateway configured",
            }

        done_predicate = request.envelope.done_predicate
        max_calls = self._tool_loop_max_calls(request.envelope)
        attempts = 0
        risk_level = self._risk_level_value(descriptor)
        requires_approval = self._requires_approval(descriptor)
        session_id = self._session_state.run_id if self._session_state is not None else None

        while True:
            attempts += 1
            self._context.budget_check()
            self._context.budget_use("tool_calls", 1)

            if requires_approval:
                allowed, approval_error = await self._resolve_tool_approval(
                    capability_id=request.capability_id,
                    params=request.params,
                    session_id=session_id,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                )
                if not allowed:
                    await self._log_event(
                        "tool.error",
                        {
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "capability_id": request.capability_id,
                            "error": approval_error,
                            "attempt": attempts,
                        },
                    )
                    await self._emit_hook(
                        HookPhase.AFTER_TOOL,
                        {
                            "tool_call_id": tool_call_id,
                            "tool_name": tool_name,
                            "capability_id": request.capability_id,
                            "attempt": attempts,
                            "success": False,
                            "error": approval_error,
                            "approved": False,
                            "evidence_collected": False,
                            "duration_ms": 0.0,
                            "budget_stats": self._budget_stats(),
                        },
                    )
                    return {
                        "success": False,
                        "error": approval_error,
                        "output": {},
                    }

            tool_start = time.perf_counter()
            await self._emit_hook(
                HookPhase.BEFORE_TOOL,
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "attempt": attempts,
                    "risk_level": risk_level,
                    "requires_approval": requires_approval,
                },
            )
            await self._log_event("tool.invoke", {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "capability_id": request.capability_id,
                "attempt": attempts,
            })

            try:
                result = await self._tool_gateway.invoke(
                    request.capability_id,
                    request.params,
                    envelope=request.envelope,
                )

                await self._log_event("tool.result", {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "success": getattr(result, "success", True),
                    "attempt": attempts,
                })

                tool_success = True
                if hasattr(result, "success") and not result.success:
                    tool_success = False
                evidence_collected = bool(getattr(result, "evidence", []))
                await self._emit_hook(
                    HookPhase.AFTER_TOOL,
                    {
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "capability_id": request.capability_id,
                        "attempt": attempts,
                        "success": tool_success,
                        "error": result.error if hasattr(result, "error") else None,
                        "approved": True,
                        "evidence_collected": evidence_collected,
                        "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                        "budget_stats": self._budget_stats(),
                    },
                )

                if not tool_success:
                    return {
                        "success": False,
                        "error": result.error or "tool failed",
                        "output": getattr(result, "output", {}),
                        "result": result,
                    }

                # Collect evidence
                milestone_state = self._session_state.current_milestone_state
                if milestone_state and hasattr(result, "evidence"):
                    for evidence in result.evidence:
                        milestone_state.add_evidence(evidence)

                if done_predicate is None or _done_predicate_satisfied(done_predicate, result):
                    return {
                        "success": True,
                        "output": getattr(result, "output", {}),
                        "error": getattr(result, "error", None),
                        "result": result,
                    }

                if max_calls is not None and attempts >= max_calls:
                    return {
                        "success": False,
                        "error": "done predicate not satisfied before budget exhausted",
                        "output": getattr(result, "output", {}),
                        "result": result,
                    }

            except Exception as e:
                await self._log_event("tool.error", {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "error": str(e),
                    "attempt": attempts,
                })
                approved = True
                try:
                    from dare_framework.tool.exceptions import HumanApprovalRequired

                    if isinstance(e, HumanApprovalRequired):
                        approved = False
                except Exception:
                    approved = True
                await self._emit_hook(
                    HookPhase.AFTER_TOOL,
                    {
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "capability_id": request.capability_id,
                        "attempt": attempts,
                        "success": False,
                        "error": str(e),
                        "approved": approved,
                        "evidence_collected": False,
                        "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                        "budget_stats": self._budget_stats(),
                    },
                )
                return {
                    "success": False,
                    "error": str(e),
                    "output": {},
                }

    async def _resolve_tool_approval(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        tool_name: str,
        tool_call_id: str,
    ) -> tuple[bool, str | None]:
        if self._approval_manager is None:
            return False, "tool requires approval but no approval manager is configured"

        evaluation = await self._approval_manager.evaluate(
            capability_id=capability_id,
            params=params,
            session_id=session_id,
            reason=f"Tool {capability_id} requires approval",
        )
        if evaluation.status == ApprovalEvaluationStatus.ALLOW:
            await self._log_event(
                "tool.approval",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": capability_id,
                    "status": "allow",
                    "source": "rule",
                    "rule_id": evaluation.rule.rule_id if evaluation.rule is not None else None,
                },
            )
            return True, None

        if evaluation.status == ApprovalEvaluationStatus.DENY:
            await self._log_event(
                "tool.approval",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": capability_id,
                    "status": "deny",
                    "source": "rule",
                    "rule_id": evaluation.rule.rule_id if evaluation.rule is not None else None,
                },
            )
            return False, "tool invocation denied by approval rule"

        if evaluation.request is None:
            return False, "tool invocation requires approval"

        request_id = evaluation.request.request_id
        await self._log_event(
            "exec.waiting_human",
            {
                "checkpoint_id": request_id,
                "reason": evaluation.request.reason,
                "mode": "approval_memory_wait",
            },
        )
        decision = await self._approval_manager.wait_for_resolution(request_id)
        await self._log_event(
            "exec.resume",
            {
                "checkpoint_id": request_id,
                "decision": decision.value,
            },
        )
        await self._log_event(
            "tool.approval",
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "capability_id": capability_id,
                "status": decision.value,
                "source": "pending_request",
                "request_id": request_id,
            },
        )
        if decision == ApprovalDecision.ALLOW:
            return True, None
        return False, "tool invocation denied by human approval"

    # =========================================================================
    # Verify
    # =========================================================================

    async def _verify_milestone(
        self,
        execute_result: dict[str, Any],
        validated_plan: ValidatedPlan | None = None,
    ) -> VerifyResult:
        """Verify that a milestone has been completed.

        Passes validated_plan to the validator so it can use step criteria
        (e.g. expected_files from code_creation_evidence) for verification.
        """
        if self._validator is None:
            return VerifyResult(success=True)

        milestone_id = None
        if self._session_state and self._session_state.current_milestone_state:
            milestone_id = self._session_state.current_milestone_state.milestone.milestone_id
        await self._emit_hook(HookPhase.BEFORE_VERIFY, {"milestone_id": milestone_id})

        # TODO: Need to convert execute_result to proper type
        # For now, create a minimal RunResult
        from dare_framework.plan.types import RunResult as PlanRunResult

        run_result = PlanRunResult(
            success=execute_result.get("success", False),
            output=execute_result.get("outputs"),
            errors=execute_result.get("errors", []),
        )

        # Call verify_milestone with plan if supported, otherwise without
        import inspect
        sig = inspect.signature(self._validator.verify_milestone)
        if 'plan' in sig.parameters:
            verify_result = await self._validator.verify_milestone(
                run_result,
                self._context,
                plan=validated_plan,
            )
        else:
            # Backward compatibility: validator doesn't support plan parameter
            verify_result = await self._validator.verify_milestone(
                run_result,
                self._context,
            )
        await self._emit_hook(HookPhase.AFTER_VERIFY, {
            "milestone_id": milestone_id,
            "success": verify_result.success,
            "errors": list(verify_result.errors),
        })
        return verify_result

    # =========================================================================
    # Helpers
    # =========================================================================

    async def _capability_index(self) -> dict[str, Any]:
        """Build a capability index from the trusted tool registry."""
        if self._tool_gateway is None:
            return {}
        try:
            capabilities = self._tool_gateway.list_capabilities()
        except Exception:
            return {}
        index: dict[str, Any] = {}
        for capability in capabilities:
            index[capability.id] = capability
            index.setdefault(capability.name, capability)
        return index

    def _is_plan_tool_call(self, name: str | None, descriptor: Any | None) -> bool:
        """Return True if the tool call should trigger a re-plan."""
        if not name:
            return False
        if name.startswith("plan:"):
            return True
        if descriptor is None or descriptor.metadata is None:
            return False
        kind = descriptor.metadata.get("capability_kind")
        if hasattr(kind, "value"):
            kind = kind.value
        return str(kind) == CapabilityKind.PLAN_TOOL.value

    def _is_skill_tool_call(self, descriptor: Any | None) -> bool:
        """Return True if the tool call is a skill selection."""
        if descriptor is None or descriptor.metadata is None:
            return False
        kind = descriptor.metadata.get("capability_kind")
        if hasattr(kind, "value"):
            kind = kind.value
        return str(kind) == CapabilityKind.SKILL.value

    def _mount_skill_from_result(self, output: Any) -> None:
        """Mount skill into context based on tool output."""
        if not isinstance(output, dict):
            return
        skill_id = output.get("skill_id")
        name = output.get("name")
        content = output.get("content")
        description = output.get("description", "")
        if not isinstance(skill_id, str) or not skill_id.strip():
            return
        if not isinstance(name, str) or not name.strip():
            return
        if not isinstance(content, str) or not content.strip():
            prompt = output.get("prompt")
            if isinstance(prompt, str) and prompt.strip():
                content = prompt
            else:
                return
        if not isinstance(description, str):
            description = ""
        skill_path = output.get("skill_path")
        scripts = output.get("scripts")
        from pathlib import Path

        skill_dir = Path(skill_path) if isinstance(skill_path, str) and skill_path else None
        script_map: dict[str, Path] = {}
        if isinstance(scripts, dict):
            for key, value in scripts.items():
                if isinstance(key, str) and isinstance(value, str) and value:
                    script_map[key] = Path(value)
        from dare_framework.skill.types import Skill

        self._context.set_skill(
            Skill(
                id=skill_id.strip(),
                name=name.strip(),
                description=description.strip(),
                content=content,
                skill_dir=skill_dir,
                scripts=script_map,
            )
        )

    def _risk_level_value(self, descriptor: Any | None) -> int:
        if descriptor is None or descriptor.metadata is None:
            return 1
        risk_level = descriptor.metadata.get("risk_level", "read_only")
        if hasattr(risk_level, "value"):
            risk_level = risk_level.value
        mapping = {
            "read_only": 1,
            "idempotent_write": 2,
            "non_idempotent_effect": 3,
            "compensatable": 4,
        }
        return mapping.get(str(risk_level), 1)

    def _requires_approval(self, descriptor: Any | None) -> bool:
        if descriptor is None or descriptor.metadata is None:
            return False
        return bool(descriptor.metadata.get("requires_approval", False))

    def _tool_loop_max_calls(self, envelope: Envelope) -> int | None:
        if envelope.budget.max_tool_calls is not None:
            return envelope.budget.max_tool_calls
        if self._context.budget.max_tool_calls is not None:
            return self._context.budget.max_tool_calls
        return self._max_tool_iterations

    def _poll_or_raise(self) -> None:
        """Poll execution control and raise if interrupted.

        TODO(@bouillipx): Confirm this method exists on IExecutionControl
        """
        if self._exec_ctl is None:
            return

        # Try poll_or_raise first
        if hasattr(self._exec_ctl, "poll_or_raise"):
            self._exec_ctl.poll_or_raise()
            return

        # Fallback to poll()
        signal = self._exec_ctl.poll()
        # TODO(@bouillipx): Handle different signal types
        # For now, just continue

    def _assemble_messages(self, assembled: AssembledContext) -> list[Message]:
        messages = list(assembled.messages)
        prompt_def = getattr(assembled, "sys_prompt", None)
        if prompt_def is None:
            return messages
        return [
            Message(
                role=prompt_def.role,
                content=prompt_def.content,
                name=prompt_def.name,
                metadata=dict(prompt_def.metadata),
            ),
            *messages,
        ]

    def _context_stats(self, messages: list[Message], tools_count: int) -> dict[str, int]:
        total_length = 0
        for message in messages:
            total_length += len(message.content or "")
        return {
            "context_length": total_length,
            "context_messages_count": len(messages),
            "context_tools_count": tools_count,
        }

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> None:
        """Emit a hook payload via the extension point (best-effort)."""
        enriched = dict(payload)
        enriched.setdefault("phase", phase.value)
        if self._session_state:
            enriched.setdefault("task_id", self._session_state.task_id)
            enriched.setdefault("run_id", self._session_state.run_id)
            enriched.setdefault("session_id", self._session_state.run_id)
        if self._extension_point is not None:
            try:
                await self._extension_point.emit(phase, enriched)
            except Exception:
                pass
        await self._emit_transport_hook(phase, enriched)

    async def _emit_transport_hook(self, phase: HookPhase, payload: dict[str, Any]) -> None:
        channel = self._active_transport
        if channel is None:
            return
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            payload={
                "type": "hook",
                "phase": phase.value,
                "payload": payload,
            },
        )
        try:
            await channel.send(envelope)
        except Exception:
            self._logger.exception("agent transport hook send failed")

    def _record_token_usage(self, usage: dict[str, Any] | None) -> None:
        if not usage:
            return
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
        cached_tokens = usage.get("cached_tokens", 0)
        try:
            self._token_usage["input_tokens"] += int(input_tokens or 0)
        except (TypeError, ValueError):
            pass
        try:
            self._token_usage["output_tokens"] += int(output_tokens or 0)
        except (TypeError, ValueError):
            pass
        try:
            self._token_usage["cached_tokens"] += int(cached_tokens or 0)
        except (TypeError, ValueError):
            pass

    def _total_tokens_from_usage(self, usage: dict[str, Any]) -> int:
        total_tokens = usage.get("total_tokens")
        if total_tokens is None:
            input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
            output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
            total_tokens = input_tokens + output_tokens
        try:
            return int(total_tokens or 0)
        except (TypeError, ValueError):
            return 0

    def _budget_stats(self) -> dict[str, Any]:
        budget = self._context.budget
        tokens_remaining = self._context.budget_remaining("tokens")
        tool_calls_remaining = self._context.budget_remaining("tool_calls")
        return {
            "tokens_used": budget.used_tokens,
            "tokens_limit": budget.max_tokens,
            "cost_used": budget.used_cost,
            "tokens_remaining": None if tokens_remaining == float("inf") else tokens_remaining,
            "tool_calls_used": budget.used_tool_calls,
            "tool_calls_remaining": None
            if tool_calls_remaining == float("inf")
            else tool_calls_remaining,
            "time_used_seconds": budget.used_time_seconds,
            "time_remaining_seconds": None
            if budget.max_time_seconds is None
            else max(0.0, budget.max_time_seconds - budget.used_time_seconds),
        }

    async def _finalize_execute(self, start_time: float, result: dict[str, Any]) -> dict[str, Any]:
        await self._emit_hook(HookPhase.AFTER_EXECUTE, {
            "success": result.get("success", False),
            "errors": result.get("errors", []),
            "duration_ms": (time.perf_counter() - start_time) * 1000.0,
            "budget_stats": self._budget_stats(),
        })
        return result

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Log an event to the event log (if configured)."""
        # Add session context
        if self._session_state:
            payload = {
                "task_id": self._session_state.task_id,
                "run_id": self._session_state.run_id,
                **payload,
            }

        if self._event_log is not None:
            await self._event_log.append(event_type, payload)


def _format_tool_result(tool_result: dict[str, Any]) -> str:
    import json

    success = bool(tool_result.get("success", False))
    result_obj = tool_result.get("result")
    output: Any = None
    error: Any = None

    if result_obj is not None and hasattr(result_obj, "output"):
        output = getattr(result_obj, "output", None)
        error = getattr(result_obj, "error", None)
    else:
        output = tool_result.get("output")
        error = tool_result.get("error")

    payload = {"success": success, "output": output}
    if error:
        payload["error"] = error

    return json.dumps(payload, ensure_ascii=True)


__all__ = ["DareAgent"]


def _done_predicate_satisfied(done_predicate: DonePredicate, result: Any) -> bool:
    required_keys = list(done_predicate.required_keys or [])
    if not required_keys:
        return True
    output = getattr(result, "output", None)
    if not isinstance(output, dict):
        return False
    for key in required_keys:
        if key not in output:
            return False
    return True
