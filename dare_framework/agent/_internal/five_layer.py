"""FiveLayerAgent - Five-layer loop agent implementation.

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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from dare_framework.agent._internal.base import BaseAgent
from dare_framework.agent._internal.orchestration import MilestoneState, SessionState
from dare_framework.agent.interfaces import IAgentOrchestration
from dare_framework.context import AssembledContext, Context, Message
from dare_framework.model import IModelAdapter, ModelInput
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
from dare_framework.tool.types import CapabilityKind


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
    from dare_framework.memory import ILongTermMemory, IShortTermMemory
    from dare_framework.plan.interfaces import IPlanner, IRemediator, IValidator
    from dare_framework.tool import IToolProvider
    from dare_framework.tool.kernel import IExecutionControl, IToolGateway


class FiveLayerAgent(BaseAgent):
    """Five-layer loop agent implementation.

    This agent implements the IAgentOrchestration interface and supports
    the full five-layer orchestration loop while allowing graceful
    degradation when optional components are not provided.

    Architecture:
        - Implements IAgentOrchestration.execute() as the core entry point
        - Overrides BaseAgent.run() to delegate to execute()
        - Preserves _execute() for BaseAgent compatibility

    Example:
        # Full five-layer mode
        agent = FiveLayerAgent(
            name="full-agent",
            model=model,
            planner=planner,
            validator=validator,
        )

        # ReAct mode (no planner/validator)
        agent = FiveLayerAgent(
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
        context: "IContext | None" = None,
        # Memory components (optional)
        short_term_memory: "IShortTermMemory | None" = None,
        long_term_memory: "ILongTermMemory | None" = None,
        # Tool components (optional)
        tools: "IToolProvider | None" = None,
        tool_gateway: "IToolGateway | None" = None,
        execution_control: "IExecutionControl | None" = None,
        # Plan components (optional - enables full five-layer mode)
        planner: "IPlanner | None" = None,
        validator: "IValidator | None" = None,
        remediator: "IRemediator | None" = None,
        # Observability components (optional)
        event_log: "IEventLog | None" = None,
        hooks: "list[IHook] | None" = None,
        # Configuration
        budget: "Budget | None" = None,
        max_milestone_attempts: int = 3,
        max_plan_attempts: int = 3,
        max_tool_iterations: int = 20,
    ) -> None:
        """Initialize FiveLayerAgent.

        Args:
            name: Agent name identifier.
            model: Model adapter for generating responses (required).
            context: Pre-configured context (optional).
            short_term_memory: Short-term memory (optional).
            long_term_memory: Long-term memory (optional).
            tools: Tool provider for listing tools (optional).
            tool_gateway: Tool gateway for invoking tools (optional).
            execution_control: Execution control for HITL (optional).
            planner: Plan generator (optional, enables full five-layer).
            validator: Plan/milestone validator (optional).
            remediator: Failure remediator (optional).
            event_log: Event log for audit (optional).
            hooks: Hook implementations invoked at lifecycle phases (optional).
            budget: Resource budget (optional).
            max_milestone_attempts: Max retries per milestone.
            max_plan_attempts: Max plan generation attempts.
            max_tool_iterations: Max tool call iterations per execute loop.
        """
        super().__init__(name)
        self._model = model

        # Create or use provided context
        if context is None:
            from dare_framework.context import Budget as BudgetClass

            self._context = Context(
                id=f"context_{name}",
                short_term_memory=short_term_memory,
                long_term_memory=long_term_memory,
                budget=budget or BudgetClass(),
            )
            if tools is not None:
                self._context._tool_provider = tools
        else:
            self._context = context

        # Tool components
        self._tool_gateway = tool_gateway
        self._exec_ctl = execution_control

        # Plan components (optional)
        self._planner = planner
        self._validator = validator
        self._remediator = remediator

        # Observability
        self._event_log = event_log
        self._hooks = list(hooks) if hooks is not None else []

        # Configuration
        self._max_milestone_attempts = max_milestone_attempts
        self._max_plan_attempts = max_plan_attempts
        self._max_tool_iterations = max_tool_iterations

        # Runtime state (set during execution)
        self._session_state: SessionState | None = None

    @property
    def context(self) -> "IContext":
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

    # =========================================================================
    # IAgentOrchestration Implementation
    # =========================================================================

    async def execute(self, task: Task, deps: Any | None = None) -> RunResult:
        """Execute task with automatic mode selection.

        This is the primary entry point implementing IAgentOrchestration.
        Mode is automatically selected based on component configuration:

        - **Full Five-Layer**: planner is provided → Session→Milestone→Plan→Execute→Tool
        - **ReAct Mode**: no planner, has tools → Execute→Tool loop directly
        - **Simple Mode**: no planner, no tools → Single model generation

        Args:
            task: Task to execute.
            deps: Optional dependencies (unused, for interface compatibility).

        Returns:
            RunResult with execution outcome.
        """
        # Full five-layer mode: has planner or task has explicit milestones
        if self.is_full_five_layer_mode or task.milestones:
            return await self._run_session_loop(task)

        # ReAct mode: no planner but has tools
        if self.is_react_mode:
            return await self._run_react_loop(task)

        # Simple mode: no planner, no tools → just model generation
        return await self._run_simple_loop(task)

    # =========================================================================
    # IAgent.run() Override
    # =========================================================================

    async def run(self, task: str | Task, deps: Any | None = None) -> RunResult:
        """Run a task and return a structured RunResult.

        Overrides BaseAgent.run() to delegate to execute().

        Args:
            task: Task description string or Task object.
            deps: Optional dependencies.

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
        return await self.execute(task_obj, deps)

    # =========================================================================
    # BaseAgent Compatibility
    # =========================================================================

    async def _execute(self, task: str) -> str:
        """Execute task - BaseAgent compatibility layer.

        This method is preserved for compatibility with BaseAgent.
        Internally delegates to execute() and converts result to string.
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

        # Add user message to STM
        user_message = Message(role="user", content=task.description)
        self._context.stm_add(user_message)

        # Budget check
        self._context.budget_check()

        # Assemble context
        assembled = self._context.assemble()

        # Create model input
        model_input = ModelInput(
            messages=self._assemble_messages(assembled),
            tools=[],  # No tools in simple mode
            metadata=assembled.metadata,
        )

        # Generate model response
        response = await self._model.generate(model_input)

        # Add response to STM
        assistant_message = Message(role="assistant", content=response.content)
        self._context.stm_add(assistant_message)

        # Record token usage
        if response.usage:
            tokens = response.usage.get("total_tokens", 0)
            if tokens:
                self._context.budget_use("tokens", tokens)

        await self._log_event("simple.complete", {
            "success": True,
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
        self._session_state = SessionState(
            task_id=task.task_id or uuid4().hex[:8],
        )

        # Log session start
        await self._log_event("session.start", {
            "task_id": self._session_state.task_id,
            "run_id": self._session_state.run_id,
        })

        # Add user message to STM
        user_message = Message(role="user", content=task.description)
        self._context.stm_add(user_message)

        # Get milestones
        milestones = task.to_milestones()

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

            # Check budget before each milestone
            # TODO(@mahaichuan-qq): Confirm exception type for budget_check()
            self._context.budget_check()

            # Check execution control
            # TODO(@bouillipx): Confirm poll_or_raise() exists
            if self._exec_ctl is not None:
                self._poll_or_raise()

            result = await self._run_milestone_loop(milestone)
            milestone_results.append(result)

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
        await self._log_event("milestone.start", {
            "milestone_id": milestone.milestone_id,
        })

        milestone_state = self._session_state.current_milestone_state

        for attempt in range(self._max_milestone_attempts):
            # Budget check
            self._context.budget_check()

            # Run plan loop (if planner available)
            validated_plan = await self._run_plan_loop(milestone)

            # Run execute loop
            execute_result = await self._run_execute_loop(validated_plan)

            # Handle plan tool encountered
            if execute_result.get("encountered_plan_tool", False):
                if milestone_state:
                    milestone_state.add_reflection(
                        f"plan tool encountered: {execute_result.get('plan_tool_name')}"
                    )
                continue

            # Verify milestone (if validator available)
            verify_result = await self._verify_milestone(execute_result)

            if verify_result.success:
                await self._log_event("milestone.success", {
                    "milestone_id": milestone.milestone_id,
                    "attempts": attempt + 1,
                })
                return MilestoneResult(
                    success=True,
                    outputs=execute_result.get("outputs", []),
                    errors=[],
                    verify_result=verify_result,
                )

            # Remediate if available
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
            # Assemble context for planning
            assembled = self._context.assemble()

            # Generate plan
            proposed = await self._planner.plan(self._context)

            await self._log_event("plan.attempt", {
                "milestone_id": milestone.milestone_id,
                "attempt": attempt + 1,
            })

            # Validate plan (if validator available)
            if self._validator is None:
                # No validator: treat proposed as validated
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
                return validated

            # Plan failed validation
            await self._log_event("plan.invalid", {
                "milestone_id": milestone.milestone_id,
                "errors": validated.errors,
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
        # Budget check
        self._context.budget_check()

        # Assemble context for execution
        assembled = self._context.assemble()

        # Create prompt
        model_input = ModelInput(
            messages=self._assemble_messages(assembled),
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
            response = await self._model.generate(model_input)

            await self._log_event("model.response", {
                "iteration": iteration + 1,
                "has_tool_calls": bool(response.tool_calls),
            })

            # No tool calls: we're done
            if not response.tool_calls:
                # Add response to STM
                assistant_message = Message(role="assistant", content=response.content)
                self._context.stm_add(assistant_message)

                # Record token usage
                if response.usage:
                    tokens = response.usage.get("total_tokens", 0)
                    if tokens:
                        self._context.budget_use("tokens", tokens)

                outputs.append({"content": response.content})
                return {
                    "success": True,
                    "outputs": outputs,
                    "errors": errors,
                }

            # Process tool calls
            capability_index = await self._capability_index() if response.tool_calls else {}
            for tool_call in response.tool_calls:
                name = tool_call.get("name", "")
                capability_id = tool_call.get("capability_id") or name
                descriptor = capability_index.get(capability_id) or capability_index.get(name)

                # Check for plan tool (registry kind preferred, prefix supported)
                if self._is_plan_tool_call(name, descriptor):
                    return {
                        "success": False,
                        "outputs": outputs,
                        "errors": errors,
                        "encountered_plan_tool": True,
                        "plan_tool_name": name,
                    }

                # Run tool loop
                tool_result = await self._run_tool_loop(
                    ToolLoopRequest(
                        capability_id=capability_id,
                        params=tool_call.get("arguments", {}),
                    )
                )
                outputs.append(tool_result)

                if not tool_result.get("success", False):
                    errors.append(tool_result.get("error", "tool failed"))

            # Update prompt with tool results for next iteration
            # (Simplified: in production would format properly)
            model_input = ModelInput(
                messages=self._assemble_messages(assembled),
                tools=assembled.tools,
                metadata=assembled.metadata,
            )

        # Max iterations reached
        errors.append("max tool iterations reached")
        return {
            "success": False,
            "outputs": outputs,
            "errors": errors,
        }

    # =========================================================================
    # Tool Loop (Layer 5)
    # =========================================================================

    async def _run_tool_loop(self, request: ToolLoopRequest) -> dict[str, Any]:
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

        while True:
            attempts += 1
            self._context.budget_check()
            self._context.budget_use("tool_calls", 1)

            await self._log_event("tool.invoke", {
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
                    "capability_id": request.capability_id,
                    "success": True,
                    "attempt": attempts,
                })

                if hasattr(result, "success") and not result.success:
                    return {
                        "success": False,
                        "error": result.error or "tool failed",
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
                        "result": result,
                    }

                if max_calls is not None and attempts >= max_calls:
                    return {
                        "success": False,
                        "error": "done predicate not satisfied before budget exhausted",
                        "result": result,
                    }

            except Exception as e:
                await self._log_event("tool.error", {
                    "capability_id": request.capability_id,
                    "error": str(e),
                    "attempt": attempts,
                })
                return {
                    "success": False,
                    "error": str(e),
                }

    # =========================================================================
    # Verify
    # =========================================================================

    async def _verify_milestone(self, execute_result: dict[str, Any]) -> VerifyResult:
        """Verify that a milestone has been completed."""
        if self._validator is None:
            # No validator: assume success
            return VerifyResult(success=True)

        # TODO: Need to convert execute_result to proper type
        # For now, create a minimal RunResult
        from dare_framework.plan.types import RunResult as PlanRunResult

        run_result = PlanRunResult(
            success=execute_result.get("success", False),
            output=execute_result.get("outputs"),
            errors=execute_result.get("errors", []),
        )

        return await self._validator.verify_milestone(run_result, self._context)

    # =========================================================================
    # Helpers
    # =========================================================================

    async def _capability_index(self) -> dict[str, Any]:
        """Build a capability index from the trusted tool registry."""
        if self._tool_gateway is None:
            return {}
        try:
            capabilities = await self._tool_gateway.list_capabilities()
        except Exception:
            return {}
        index: dict[str, Any] = {}
        for capability in capabilities:
            index[capability.id] = capability
            index.setdefault(capability.name, capability)
        return index

    def _is_plan_tool_call(self, name: str, descriptor: Any | None) -> bool:
        """Return True if the tool call should trigger a re-plan."""
        if name.startswith("plan:"):
            return True
        if descriptor is None or descriptor.metadata is None:
            return False
        kind = descriptor.metadata.get("capability_kind")
        if hasattr(kind, "value"):
            kind = kind.value
        return str(kind) == CapabilityKind.PLAN_TOOL.value

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

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Log an event to the event log (if configured)."""
        if self._event_log is None:
            return

        # Add session context
        if self._session_state:
            payload = {
                "task_id": self._session_state.task_id,
                "run_id": self._session_state.run_id,
                **payload,
            }

        await self._event_log.append(event_type, payload)


__all__ = ["FiveLayerAgent"]


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
