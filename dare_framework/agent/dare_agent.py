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
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from dare_framework.agent._internal.input_normalizer import build_task_from_message
from dare_framework.agent._internal.output_normalizer import build_output_envelope
from dare_framework.agent._internal.execute_engine import run_execute_loop
from dare_framework.agent._internal.milestone_orchestrator import run_milestone_loop
from dare_framework.agent._internal.orchestration import MilestoneResult, SessionState
from dare_framework.agent._internal.session_orchestrator import run_session_loop
from dare_framework.agent._internal.tool_executor import run_tool_loop
from dare_framework.agent.base_agent import BaseAgent
from dare_framework.context import AssembledContext, Message
from dare_framework.hook._internal.hook_extension_point import HookExtensionPoint
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
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
    StepResult,
    Task,
    ToolLoopRequest,
    ValidatedPlan,
    ValidatedStep,
    VerifyResult,
)
from dare_framework.security import (
    DefaultSecurityBoundary,
    ISecurityBoundary,
    PolicyDecision,
    RiskLevel,
    SandboxSpec,
    SECURITY_APPROVAL_MANAGER_MISSING,
    SECURITY_POLICY_CHECK_FAILED,
    SECURITY_POLICY_DENIED,
    SECURITY_TRUST_DERIVATION_FAILED,
    SecurityBoundaryError,
    TrustedInput,
)
from dare_framework.tool._internal.governed_tool_gateway import (
    GovernedToolGateway,
)
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalEvaluationStatus,
)
from dare_framework.tool.types import CapabilityKind
from dare_framework.transport.interaction.payloads import (
    build_approval_pending_payload,
    build_approval_resolved_payload,
)
from dare_framework.transport.types import (
    EnvelopeKind,
    TransportEnvelope,
    new_envelope_id,
)


class EventLogWriteError(RuntimeError):
    """Raised when runtime event persistence fails."""


@dataclass(frozen=True)
class SecurityPreflightResult:
    """Outcome of tool security preflight checks."""

    trusted_input: TrustedInput
    decision: PolicyDecision
    reason: str | None = None
if TYPE_CHECKING:
    from dare_framework.config.types import Config
    from dare_framework.context.kernel import IContext
    from dare_framework.event.kernel import IEventLog
    from dare_framework.hook.kernel import IHook
    from dare_framework.mcp.manager import MCPManager
    from dare_framework.observability.kernel import ITelemetryProvider
    from dare_framework.plan.interfaces import IPlanner, IRemediator, IValidator
    from dare_framework.security.kernel import ISecurityBoundary
    from dare_framework.tool.interfaces import IExecutionControl
    from dare_framework.tool.kernel import IToolGateway, IToolManager, IToolProvider
    from dare_framework.tool._internal.control.approval_manager import ToolApprovalManager
    from dare_framework.tool.types import ToolDefinition
    from dare_framework.transport.kernel import AgentChannel


class DareAgent(BaseAgent):
    """DARE Framework agent implementation.

    This agent implements the IAgentOrchestration interface and supports
    the full five-layer orchestration loop while allowing graceful
    degradation when optional components are not provided.

    Architecture:
        - Implements IAgentOrchestration.execute() as the core entry point

    Mode:
        - **Five-Layer Only**: Session→Milestone→Plan→Execute→Tool

    Example:
        # Full five-layer mode
        agent = await (
            BaseAgent.dare_agent_builder("full-agent")
            .with_model(model)
            .with_planner(planner)
            .add_validators(validator)
            .build()
        )
    """

    def __init__(
        self,
        name: str,
        *,
        model: IModelAdapter,
        context: IContext,
        # Tool components
        tool_gateway: IToolGateway,
        mcp_manager: MCPManager | None = None,
        execution_control: IExecutionControl | None = None,
        security_boundary: ISecurityBoundary | None = None,
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
            context: Pre-configured context (required, provided by builder).
            tool_gateway: Tool gateway for invoking tools (required, provided by builder).
            execution_control: Execution control for HITL (optional).
            security_boundary: Security boundary for trust/policy/sandbox checks (optional).
            approval_manager: Tool approval manager for persisted approval memory (optional).
            planner: Plan generator (optional, enables full five-layer).
            validator: Plan/milestone validator (optional).
            remediator: Failure remediator (optional).
            event_log: Event log for audit (optional).
            hooks: Hook implementations invoked at lifecycle phases (optional).
            telemetry: Telemetry provider for traces/metrics/logs (optional).
            security_boundary: Security boundary used for trust/policy preflight.
            max_milestone_attempts: Max retries per milestone.
            max_plan_attempts: Max plan generation attempts.
            max_tool_iterations: Max tool call iterations per execute loop.
            sandbox: Plan attempt sandbox for state isolation (optional).
            step_executor: Step executor for step-driven mode (optional).
            evidence_collector: Evidence collector for verification (optional).
            execution_mode: "model_driven" (default) or "step_driven".
        """
        super().__init__(name, agent_channel=agent_channel)
        normalized_execution_mode = execution_mode.strip().lower()
        if normalized_execution_mode not in {"model_driven", "step_driven"}:
            raise ValueError("execution_mode must be 'model_driven' or 'step_driven'")
        if normalized_execution_mode == "step_driven" and planner is None:
            raise ValueError("step_driven execution requires planner")
        # Planner output in step-driven mode must pass validator-derived trust/policy metadata.
        if normalized_execution_mode == "step_driven" and planner is not None and validator is None:
            raise ValueError("step_driven execution with planner requires validator")

        self._model = model
        self._logger = logging.getLogger("dare.agent")
        self._context = context
        self._context.set_tool_gateway(tool_gateway)

        # Tool components
        self._tool_gateway = tool_gateway
        self._governed_tool_gateway = GovernedToolGateway(
            tool_gateway,
            approval_manager=approval_manager,
            logger=self._logger,
        )
        self._mcp_manager = mcp_manager
        self._exec_ctl = execution_control
        self._security_boundary = security_boundary or DefaultSecurityBoundary()
        self._approval_manager = approval_manager

        # Plan components (optional)
        self._planner = planner
        self._validator = validator
        self._remediator = remediator

        # Milestone orchestration components (optional)
        self._sandbox = sandbox
        self._step_executor = step_executor
        self._evidence_collector = evidence_collector
        self._execution_mode = normalized_execution_mode

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
        self._conversation_id: str | None = None
        self._token_usage: dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "total_tokens": 0,
        }

    @property
    def context(self) -> IContext:
        """Agent context."""
        return self._context

    @property
    def is_full_five_layer_mode(self) -> bool:
        """Check if agent has full five-layer capabilities."""
        return self._planner is not None

    @property
    def supports_mcp_management(self) -> bool:
        """Whether runtime MCP management APIs are available on this agent."""
        try:
            self._require_tool_manager()
            self._require_mcp_manager()
        except RuntimeError:
            return False
        return True

    async def reload_mcp(
        self,
        *,
        config: Config | None = None,
        paths: list[str | Path] | None = None,
    ) -> IToolProvider:
        """Reload MCP providers and refresh registry state."""
        manager = self._require_mcp_manager()
        tool_manager = self._require_tool_manager()
        return await manager.reload(tool_manager, config=config, paths=paths)

    async def unload_mcp(self) -> bool:
        """Unload active MCP providers from the registry."""
        manager = self._require_mcp_manager()
        tool_manager = self._require_tool_manager()
        return await manager.unload(tool_manager)

    def inspect_mcp_tools(self, *, tool_name: str | None = None) -> list[ToolDefinition]:
        """Inspect currently exposed MCP tool definitions."""
        manager = self._require_mcp_manager()
        tool_manager = self._require_tool_manager()
        return manager.list_mcp_tool_defs(tool_manager, tool_name=tool_name)

    def list_tool_defs(self) -> list[ToolDefinition]:
        """List all tool definitions currently visible to the model."""
        return self._require_tool_manager().list_tool_defs()

    def _require_tool_manager(self) -> IToolManager:
        from dare_framework.tool.kernel import IToolManager

        if isinstance(self._tool_gateway, IToolManager):
            return self._tool_gateway
        candidate = getattr(self._tool_gateway, "_tool_manager", None)
        if isinstance(candidate, IToolManager):
            return candidate
        raise RuntimeError("Tool gateway does not support provider management.")

    def _require_mcp_manager(self) -> MCPManager:
        if self._mcp_manager is None:
            raise RuntimeError("MCP manager is not configured on this agent.")
        return self._mcp_manager

    def _log(self, message: str) -> None:
        """Write debug messages when verbose mode is enabled."""
        if self._verbose:
            self._logger.debug("[DareAgent] %s", message)

    async def execute(
        self,
        task: Message,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Execute a task with automatic mode selection."""
        previous_conversation_id = self._conversation_id
        task_obj = build_task_from_message(task)
        self._conversation_id = self._extract_conversation_id(task_obj)
        start_time = time.perf_counter()
        if task_obj.task_id is None:
            task_obj = replace(task_obj, task_id=uuid4().hex[:8])
        self._session_state = SessionState(task_id=task_obj.task_id)
        self._token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "total_tokens": 0,
        }
        execution_mode = "five_layer"
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
            result = await self._run_session_loop(task_obj, transport=transport)
            result = self._with_output_envelope(result)
            return self._with_normalized_output_text(result)
        except Exception as exc:
            error = exc
            raise
        finally:
            self._conversation_id = previous_conversation_id
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            errors: list[str] = []
            if result is not None and result.errors:
                errors.extend([str(item) for item in result.errors])
            if error is not None:
                errors.append(str(error))
            token_usage = {
                "input_tokens": self._token_usage.get("input_tokens", 0),
                "output_tokens": self._token_usage.get("output_tokens", 0),
                "total_tokens": self._token_usage.get("total_tokens", 0),
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

    # =========================================================================
    # Session Loop (Layer 1)
    # =========================================================================

    async def _run_session_loop(
        self,
        task: Task,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Run the session loop - top-level task lifecycle."""
        return await run_session_loop(self, task, transport=transport)

    # =========================================================================
    # Milestone Loop (Layer 2)
    # =========================================================================

    async def _run_milestone_loop(
        self,
        milestone: Milestone,
        *,
        transport: AgentChannel | None = None,
    ) -> MilestoneResult:
        """Run the milestone loop - sub-goal tracking."""
        return await run_milestone_loop(self, milestone, transport=transport)

    # =========================================================================
    # Plan Loop (Layer 3)
    # =========================================================================

    async def _run_plan_loop(self, milestone: Milestone) -> ValidatedPlan | None:
        """Run the plan loop - plan generation and validation.

        Returns None if no planner is configured.
        """
        if self._planner is None:
            return None  # Skip planning, continue with execute loop

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

    async def _run_execute_loop(
        self,
        plan: ValidatedPlan | None,
        *,
        transport: AgentChannel | None = None,
    ) -> dict[str, Any]:
        """Run the execute loop - model-driven execution."""
        return await run_execute_loop(self, plan, transport=transport)

    async def _run_step_driven_execute_loop(
        self,
        plan: ValidatedPlan | None,
        execute_start: float,
        *,
        transport: AgentChannel | None = None,
    ) -> dict[str, Any]:
        """Run execute loop using validated steps and a step executor."""
        outputs: list[Any] = []
        errors: list[str] = []

        # Step-driven mode is strict: a validated plan with steps is required.
        if plan is None:
            return await self._finalize_execute(execute_start, {
                "success": False,
                "outputs": outputs,
                "errors": ["step-driven execution requires a validated plan"],
            })
        if not plan.success:
            return await self._finalize_execute(execute_start, {
                "success": False,
                "outputs": outputs,
                "errors": list(plan.errors) or ["validated plan is not successful"],
            })
        if not plan.steps:
            return await self._finalize_execute(execute_start, {
                "success": False,
                "outputs": outputs,
                "errors": ["step-driven execution requires validated plan steps"],
            })

        step_executor = self._step_executor
        use_tool_loop_executor = step_executor is None
        evidence_collector: Any | None = None
        if use_tool_loop_executor:
            from dare_framework.agent._internal.step_executor import DefaultEvidenceCollector

            evidence_collector = self._evidence_collector
            if evidence_collector is None:
                evidence_collector = DefaultEvidenceCollector()
                self._evidence_collector = evidence_collector

        previous_results: list[StepResult] = []
        for step in plan.steps:
            self._context.budget_check()
            if self._exec_ctl is not None:
                self._poll_or_raise()

            descriptor = self._find_capability_descriptor(step.capability_id)
            step_capability_kind = None
            if isinstance(step.metadata, dict):
                step_capability_kind = step.metadata.get("capability_kind")
                if hasattr(step_capability_kind, "value"):
                    step_capability_kind = step_capability_kind.value

            if (
                self._is_plan_tool_call(step.capability_id, descriptor)
                or str(step_capability_kind) == CapabilityKind.PLAN_TOOL.value
            ):
                return await self._finalize_execute(execute_start, {
                    "success": False,
                    "outputs": outputs,
                    "errors": errors,
                    "encountered_plan_tool": True,
                    "plan_tool_name": step.capability_id,
                })

            if use_tool_loop_executor:
                step_result = await self._execute_step_via_tool_loop(
                    step,
                    previous_results,
                    transport=transport,
                    evidence_collector=evidence_collector,
                )
            else:
                # Custom step executors may bypass tool-loop accounting; keep
                # tool-call budgets aligned with one-step-one-tool execution.
                self._context.budget_use("tool_calls", 1)
                step_result = await self._execute_step_via_custom_executor(
                    step_executor,
                    step,
                    previous_results,
                    transport=transport,
                )
            previous_results.append(step_result)

            if step_result.success:
                outputs.append(step_result.output)
                continue

            errors.extend(step_result.errors or [f"step {step.step_id} failed"])
            return await self._finalize_execute(execute_start, {
                "success": False,
                "outputs": outputs,
                "errors": errors,
            })

        return await self._finalize_execute(execute_start, {
            "success": True,
            "outputs": outputs,
            "errors": errors,
        })

    async def _execute_step_via_tool_loop(
        self,
        step: ValidatedStep,
        previous_results: list[StepResult],
        *,
        transport: AgentChannel | None,
        evidence_collector: Any,
    ) -> StepResult:
        step_context = self._build_step_context_from_previous(previous_results)
        descriptor = self._find_capability_descriptor(step.capability_id)
        request = ToolLoopRequest(
            capability_id=step.capability_id,
            params={**step.params, **step_context},
            envelope=step.envelope or Envelope(risk_level=step.risk_level),
        )
        metadata_requires_approval = step.metadata.get("requires_approval")
        requires_approval_override = metadata_requires_approval if isinstance(metadata_requires_approval, bool) else None
        tool_result = await self._run_tool_loop(
            request,
            transport=transport,
            tool_name=step.capability_id,
            tool_call_id=f"step-{step.step_id}",
            descriptor=descriptor,
            requires_approval_override=requires_approval_override,
            trusted_risk_level_override=step.risk_level,
        )
        if tool_result.get("success"):
            # Expose plain tool output for step chaining; `result` carries
            # internal wrapper details and should not leak into step outputs.
            if "output" in tool_result:
                # Preserve explicit None payloads; only fallback when output is absent.
                result_payload = tool_result.get("output")
            else:
                result_payload = tool_result.get("result")
            evidence = evidence_collector.collect(
                source=step.capability_id,
                data={"result": result_payload, "params": step.params},
                evidence_type="tool_result",
            )
            return StepResult(
                step_id=step.step_id,
                success=True,
                output=result_payload,
                evidence=[evidence],
            )

        error = str(tool_result.get("error") or f"step {step.step_id} failed")
        return StepResult(
            step_id=step.step_id,
            success=False,
            output=tool_result.get("output"),
            errors=[error],
        )

    async def _execute_step_via_custom_executor(
        self,
        step_executor: IStepExecutor,
        step: ValidatedStep,
        previous_results: list[StepResult],
        *,
        transport: AgentChannel | None = None,
    ) -> StepResult:
        """Execute custom step executors behind the same security gates."""
        _ = transport
        tool_name = step.capability_id
        tool_call_id = f"step-{step.step_id}"
        attempt = 1
        tool_start = time.perf_counter()

        async def _emit_after_tool(
            *,
            success: bool,
            error: str | None,
            approved: bool,
            evidence_collected: bool,
            policy_decision: str | None = None,
        ) -> None:
            await self._emit_hook(
                HookPhase.AFTER_TOOL,
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "capability_id": step.capability_id,
                    "attempt": attempt,
                    "success": success,
                    "error": error,
                    "approved": approved,
                    "policy_decision": policy_decision,
                    "evidence_collected": evidence_collected,
                    "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                    "budget_stats": self._budget_stats(),
                },
            )

        step_context = self._build_step_context_from_previous(previous_results)
        descriptor = self._find_capability_descriptor(step.capability_id)
        envelope = step.envelope or Envelope(risk_level=step.risk_level)
        risk_level = max(
            self._risk_level_value(descriptor),
            self._risk_level_value_from_envelope(envelope),
        )
        descriptor_requires_approval = self._requires_approval(descriptor)
        metadata_requires_approval = step.metadata.get("requires_approval")
        requires_approval = descriptor_requires_approval
        if isinstance(metadata_requires_approval, bool):
            requires_approval = requires_approval or metadata_requires_approval

        try:
            trusted_params, trust_error = await self._resolve_tool_security(
                capability_id=step.capability_id,
                params={**step.params, **step_context},
                tool_name=tool_name,
                risk_level=risk_level,
                requires_approval=requires_approval,
                trusted_risk_level=self._coerce_risk_level(risk_level),
            )
        except Exception as exc:
            error_text = str(exc)
            await _emit_after_tool(
                success=False,
                error=error_text,
                approved=False,
                evidence_collected=False,
            )
            return StepResult(
                step_id=step.step_id,
                success=False,
                output=None,
                errors=[error_text],
            )

        approval_required_by_policy = trust_error == "tool invocation requires security approval"
        if trust_error is not None and not approval_required_by_policy:
            await _emit_after_tool(
                success=False,
                error=trust_error,
                approved=False,
                evidence_collected=False,
            )
            return StepResult(
                step_id=step.step_id,
                success=False,
                output=None,
                errors=[trust_error],
            )
        if approval_required_by_policy:
            trust_error = None
        effective_requires_approval = requires_approval or approval_required_by_policy

        before_tool_dispatch = await self._emit_hook(
            HookPhase.BEFORE_TOOL,
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "capability_id": step.capability_id,
                "attempt": attempt,
                "risk_level": risk_level,
                "requires_approval": effective_requires_approval,
            },
        )
        if before_tool_dispatch.decision in {HookDecision.BLOCK, HookDecision.ASK}:
            policy_error = (
                "tool invocation requires hook approval"
                if before_tool_dispatch.decision is HookDecision.ASK
                else "tool invocation denied by hook policy"
            )
            await _emit_after_tool(
                success=False,
                error=policy_error,
                approved=False,
                evidence_collected=False,
                policy_decision=(
                    "hook_ask" if before_tool_dispatch.decision is HookDecision.ASK
                    else "hook_block"
                ),
            )
            return StepResult(
                step_id=step.step_id,
                success=False,
                output=None,
                errors=[policy_error],
            )

        # Custom step executors bypass governed gateway invocation, so approval
        # gating must be enforced explicitly in this path.
        if effective_requires_approval:
            approved, approval_error = await self._resolve_tool_approval(
                capability_id=step.capability_id,
                params=trusted_params,
                session_id=self._session_state.run_id if self._session_state is not None else None,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                transport=transport,
            )
            if not approved:
                approval_error_text = approval_error or "tool invocation requires security approval"
                await _emit_after_tool(
                    success=False,
                    error=approval_error_text,
                    approved=False,
                    evidence_collected=False,
                )
                return StepResult(
                    step_id=step.step_id,
                    success=False,
                    output=None,
                    errors=[approval_error_text],
                )

        secured_step = replace(step, params=trusted_params, envelope=envelope)
        try:
            result = await self._security_boundary.execute_safe(
                action="invoke_tool",
                fn=lambda: step_executor.execute_step(
                    secured_step,
                    self._context,
                    previous_results,
                ),
                sandbox=SandboxSpec(
                    mode="step_executor",
                    details={
                        "capability_id": step.capability_id,
                        "step_id": step.step_id,
                        "executor": step_executor.__class__.__name__,
                    },
                ),
            )
        except Exception as exc:
            error_text = str(exc)
            await _emit_after_tool(
                success=False,
                error=error_text,
                approved=True,
                evidence_collected=False,
                policy_decision="allow",
            )
            return StepResult(
                step_id=step.step_id,
                success=False,
                output=None,
                errors=[error_text],
            )

        if isinstance(result, StepResult):
            result_error = None
            if not result.success:
                result_error = result.errors[0] if result.errors else f"step {step.step_id} failed"
            await _emit_after_tool(
                success=result.success,
                error=result_error,
                approved=True,
                evidence_collected=bool(result.evidence),
                policy_decision="allow",
            )
            return result

        invalid_error = "step executor returned invalid StepResult"
        await _emit_after_tool(
            success=False,
            error=invalid_error,
            approved=True,
            evidence_collected=False,
            policy_decision="allow",
        )
        return StepResult(
            step_id=step.step_id,
            success=False,
            output=None,
            errors=[invalid_error],
        )

    def _build_step_context_from_previous(
        self,
        previous_results: list[StepResult],
    ) -> dict[str, Any]:
        if not previous_results:
            return {}

        last_success = next(
            (result for result in reversed(previous_results) if result.success),
            None,
        )
        if last_success is None:
            return {}
        return {"_previous_output": last_success.output}

    def _find_capability_descriptor(self, capability_id: str) -> Any | None:
        try:
            for descriptor in self._tool_gateway.list_capabilities():
                if getattr(descriptor, "id", None) == capability_id:
                    return descriptor
        except Exception:
            return None
        return None

    # =========================================================================
    # Tool Loop (Layer 5)
    # =========================================================================

    async def _run_tool_loop(
        self,
        request: ToolLoopRequest,
        *,
        transport: AgentChannel | None = None,
        tool_name: str,
        tool_call_id: str,
        descriptor: Any | None = None,
        requires_approval_override: bool | None = None,
        trusted_risk_level_override: RiskLevel | None = None,
    ) -> dict[str, Any]:
        """Run the tool loop - single tool invocation."""
        extra_kwargs: dict[str, Any] = {}
        if requires_approval_override is not None:
            extra_kwargs["requires_approval_override"] = requires_approval_override
        if trusted_risk_level_override is not None:
            extra_kwargs["trusted_risk_level_override"] = trusted_risk_level_override
        return await run_tool_loop(
            self,
            request,
            transport=transport,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            descriptor=descriptor,
            **extra_kwargs,
        )

    async def _check_plan_policy(
        self,
        milestone: Milestone,
        validated_plan: ValidatedPlan | None,
    ) -> tuple[str | None, str]:
        decision = await self._security_boundary.check_policy(
            action="execute_plan",
            resource=milestone.milestone_id,
            context={
                "milestone_id": milestone.milestone_id,
                "plan_present": validated_plan is not None,
                "plan_success": validated_plan.success if validated_plan is not None else None,
                "plan_steps_count": len(validated_plan.steps) if validated_plan is not None else 0,
            },
        )
        if decision is PolicyDecision.ALLOW:
            return None, "allow"
        if decision is PolicyDecision.APPROVE_REQUIRED:
            return "execute plan requires security approval", "approve_required"
        return "execute plan denied by security policy", "deny"

    async def _resolve_tool_security(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        tool_name: str,
        risk_level: int,
        requires_approval: bool,
        trusted_risk_level: RiskLevel | None = None,
    ) -> tuple[dict[str, Any], str | None]:
        try:
            preflight = await self._evaluate_tool_security(
                request=ToolLoopRequest(
                    capability_id=capability_id,
                    params=dict(params),
                ),
                descriptor=self._find_capability_descriptor(capability_id),
                tool_name=tool_name,
                tool_call_id=f"security-preflight:{capability_id}",
                attempt=1,
                requires_approval_override=requires_approval,
                trusted_risk_level_override=trusted_risk_level,
            )
        except SecurityBoundaryError as exc:
            return {}, str(exc).strip() or "tool invocation denied by security policy"

        if preflight.decision is PolicyDecision.ALLOW:
            return dict(preflight.trusted_input.params), None
        if preflight.decision is PolicyDecision.APPROVE_REQUIRED:
            return dict(preflight.trusted_input.params), "tool invocation requires security approval"
        return {}, preflight.reason or "tool invocation denied by security policy"

    async def _resolve_tool_approval(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        tool_name: str,
        tool_call_id: str,
        transport: AgentChannel | None = None,
    ) -> tuple[bool, str | None]:
        if self._approval_manager is None:
            return False, "tool requires approval but no approval manager is configured"

        try:
            evaluation = await self._approval_manager.evaluate(
                capability_id=capability_id,
                params=params,
                session_id=session_id,
                reason=f"Tool {capability_id} requires approval",
            )
        except Exception as exc:
            error = f"tool approval evaluation failed: {exc}"
            try:
                await self._log_event(
                    "tool.approval",
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "capability_id": capability_id,
                        "status": "error",
                        "source": "evaluate",
                        "error": str(exc),
                    },
                )
            except Exception:
                self._logger.exception("approval evaluation error event emission failed")
            return False, error
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
        await self._emit_approval_pending_message(
            request=evaluation.request.to_dict(),
            transport=transport,
            capability_id=capability_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )
        await self._log_event(
            "exec.waiting_human",
            {
                "checkpoint_id": request_id,
                "reason": evaluation.request.reason,
                "mode": "approval_memory_wait",
            },
        )
        try:
            decision = await self._approval_manager.wait_for_resolution(request_id)
        except Exception as exc:
            error = f"tool approval resolution failed: {exc}"
            try:
                await self._log_event(
                    "tool.approval",
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "capability_id": capability_id,
                        "status": "error",
                        "source": "pending_request",
                        "request_id": request_id,
                        "error": str(exc),
                    },
                )
            except Exception:
                self._logger.exception("approval resolution error event emission failed")
            return False, error
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
        await self._emit_approval_resolved_message(
            request_id=request_id,
            decision=decision.value,
            transport=transport,
            capability_id=capability_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )
        if decision == ApprovalDecision.ALLOW:
            return True, None
        return False, "tool invocation denied by human approval"

    async def _emit_approval_pending_message(
        self,
        *,
        request: dict[str, Any],
        transport: AgentChannel | None,
        capability_id: str,
        tool_name: str,
        tool_call_id: str,
    ) -> None:
        if transport is None:
            return
        payload = build_approval_pending_payload(
            request=request,
            capability_id=capability_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.SELECT,
            payload=payload,
        )
        try:
            await transport.send(envelope)
        except Exception:
            self._logger.exception("approval pending transport send failed")

    async def _emit_approval_resolved_message(
        self,
        *,
        request_id: str,
        decision: str,
        transport: AgentChannel | None,
        capability_id: str,
        tool_name: str,
        tool_call_id: str,
    ) -> None:
        if transport is None:
            return
        payload = build_approval_resolved_payload(
            request_id=request_id,
            decision=decision,
            capability_id=capability_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.SELECT,
            payload=payload,
        )
        try:
            await transport.send(envelope)
        except Exception:
            self._logger.exception("approval resolved transport send failed")

    def _coerce_risk_level(self, risk_level: int) -> RiskLevel:
        mapping = {
            1: RiskLevel.READ_ONLY,
            2: RiskLevel.IDEMPOTENT_WRITE,
            3: RiskLevel.NON_IDEMPOTENT_EFFECT,
            4: RiskLevel.COMPENSATABLE,
        }
        return mapping.get(risk_level, RiskLevel.READ_ONLY)
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
        before_verify_dispatch = await self._emit_hook(HookPhase.BEFORE_VERIFY, {"milestone_id": milestone_id})
        if before_verify_dispatch.decision in {HookDecision.BLOCK, HookDecision.ASK}:
            policy_error = (
                "milestone verification requires hook approval"
                if before_verify_dispatch.decision is HookDecision.ASK
                else "milestone verification denied by hook policy"
            )
            return VerifyResult(
                success=False,
                errors=[policy_error],
            )

        # TODO: Need to convert execute_result to proper type
        # For now, create a minimal RunResult
        from dare_framework.plan.types import RunResult as PlanRunResult

        run_result = PlanRunResult(
            success=execute_result.get("success", False),
            output=execute_result.get("outputs"),
            errors=execute_result.get("errors", []),
        )

        import inspect

        verify_signature = inspect.signature(self._validator.verify_milestone)
        if "plan" in verify_signature.parameters:
            verify_result = await self._validator.verify_milestone(
                run_result,
                self._context,
                plan=validated_plan,
            )
        else:
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

    async def _evaluate_tool_security(
        self,
        *,
        request: ToolLoopRequest,
        descriptor: Any | None,
        tool_name: str,
        tool_call_id: str,
        attempt: int,
        requires_approval_override: bool | None = None,
        trusted_risk_level_override: RiskLevel | None = None,
    ) -> SecurityPreflightResult:
        requires_approval = self._requires_approval(descriptor)
        if isinstance(requires_approval_override, bool):
            requires_approval = requires_approval or requires_approval_override
        trust_context: dict[str, Any] = {
            "capability_id": request.capability_id,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "attempt": attempt,
            "descriptor": descriptor,
            "requires_approval": requires_approval,
        }
        if trusted_risk_level_override is not None:
            trust_context["risk_level"] = trusted_risk_level_override
        try:
            trusted_input = await self._security_boundary.verify_trust(
                input=dict(request.params),
                context=trust_context,
            )
        except SecurityBoundaryError as exc:
            await self._log_event(
                "security.trust_verified",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "status": "failed",
                    "code": exc.code,
                    "reason": exc.reason,
                },
            )
            raise
        except Exception as exc:
            message = str(exc).strip() or "security trust verification failed"
            await self._log_event(
                "security.trust_verified",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "status": "failed",
                    "code": SECURITY_TRUST_DERIVATION_FAILED,
                    "reason": message,
                },
            )
            raise SecurityBoundaryError(
                code=SECURITY_TRUST_DERIVATION_FAILED,
                message=message,
                reason=message,
            ) from exc

        await self._log_event(
            "security.trust_verified",
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "capability_id": request.capability_id,
                "status": "verified",
                "risk_level": trusted_input.risk_level.value,
                "requires_approval": bool(trusted_input.metadata.get("requires_approval", False)),
            },
        )

        policy_context = {
            **trust_context,
            "trusted_input": trusted_input,
            "risk_level": trusted_input.risk_level.value,
            "requires_approval": bool(trusted_input.metadata.get("requires_approval", False)),
            "metadata": dict(trusted_input.metadata),
        }
        try:
            decision = await self._security_boundary.check_policy(
                action="invoke_tool",
                resource=request.capability_id,
                context=policy_context,
            )
            if not isinstance(decision, PolicyDecision):
                raw_value = getattr(decision, "value", decision)
                try:
                    decision = PolicyDecision(str(raw_value))
                except ValueError as exc:
                    raise SecurityBoundaryError(
                        code=SECURITY_POLICY_CHECK_FAILED,
                        message=f"unsupported policy decision: {raw_value!r}",
                        reason="security boundary returned unknown policy decision",
                    ) from exc
        except SecurityBoundaryError:
            raise
        except Exception as exc:
            message = str(exc).strip() or "security policy check failed"
            raise SecurityBoundaryError(
                code=SECURITY_POLICY_CHECK_FAILED,
                message=message,
                reason=message,
            ) from exc

        reason = self._derive_policy_reason(
            decision=decision,
            capability_id=request.capability_id,
            trusted_input=trusted_input,
        )
        await self._log_event(
            "security.policy_checked",
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "capability_id": request.capability_id,
                "decision": decision.value,
                "reason": reason,
            },
        )
        return SecurityPreflightResult(
            trusted_input=trusted_input,
            decision=decision,
            reason=reason,
        )

    def _derive_policy_reason(
        self,
        *,
        decision: PolicyDecision,
        capability_id: str,
        trusted_input: TrustedInput,
    ) -> str | None:
        metadata = dict(trusted_input.metadata)
        if decision is PolicyDecision.ALLOW:
            return None
        if decision is PolicyDecision.APPROVE_REQUIRED:
            raw_reason = metadata.get("approval_reason")
            if isinstance(raw_reason, str) and raw_reason.strip():
                return raw_reason.strip()
            return f"security policy requires approval for capability '{capability_id}'"
        raw_reason = metadata.get("deny_reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            return raw_reason.strip()
        return f"security policy denied capability '{capability_id}'"

    def _risk_level_from_trusted_input(self, trusted_input: TrustedInput) -> int:
        mapping = {
            "read_only": 1,
            "idempotent_write": 2,
            "non_idempotent_effect": 3,
            "compensatable": 4,
        }
        return mapping.get(trusted_input.risk_level.value, 1)

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

    def _risk_level_value_from_envelope(self, envelope: Envelope | None) -> int:
        if envelope is None:
            return 1
        risk_level = envelope.risk_level
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
                text=prompt_def.content,
                name=prompt_def.name,
                metadata=dict(prompt_def.metadata),
            ),
            *messages,
        ]

    def _context_stats(self, messages: list[Message], tools_count: int) -> dict[str, int]:
        total_length = 0
        for message in messages:
            total_length += len(message.text or "")
        return {
            "context_length": total_length,
            "context_messages_count": len(messages),
            "context_tools_count": tools_count,
        }

    def _apply_context_patch(
        self,
        assembled: AssembledContext,
        dispatch: HookResult,
    ) -> tuple[list[Message], list[Any], dict[str, Any]]:
        messages = self._assemble_messages(assembled)
        tools: list[Any] = list(assembled.tools)
        metadata: dict[str, Any] = dict(assembled.metadata)
        patch = dispatch.patch if isinstance(dispatch.patch, dict) else None
        if patch is None:
            return messages, tools, metadata
        context_patch = patch.get("context_patch")
        if not isinstance(context_patch, dict):
            return messages, tools, metadata
        if isinstance(context_patch.get("messages"), list):
            messages = list(context_patch["messages"])
        if isinstance(context_patch.get("tools"), list):
            tools = list(context_patch["tools"])
        if isinstance(context_patch.get("metadata"), dict):
            metadata.update(context_patch["metadata"])
        return messages, tools, metadata

    def _apply_model_input_patch(self, model_input: ModelInput, dispatch: HookResult) -> ModelInput:
        patch = dispatch.patch if isinstance(dispatch.patch, dict) else None
        if patch is None:
            return model_input
        patched = patch.get("model_input")
        if isinstance(patched, ModelInput):
            return patched
        if isinstance(patched, dict):
            messages = patched.get("messages", model_input.messages)
            tools = patched.get("tools", model_input.tools)
            metadata = dict(model_input.metadata)
            if isinstance(patched.get("metadata"), dict):
                metadata.update(patched["metadata"])
            if isinstance(messages, list) and isinstance(tools, list):
                return ModelInput(messages=messages, tools=tools, metadata=metadata)
        return model_input

    def _log_model_messages(self, messages: list[Message], *, stage: str) -> None:
        """Emit message trace in verbose mode without writing to stdout."""
        if not self._verbose:
            return
        for idx, message in enumerate(messages):
            self._logger.debug(
                "[DareAgent][%s][%s] role=%s content=%s",
                stage,
                idx,
                message.role,
                message.text,
            )

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> HookResult:
        """Emit a hook payload via the extension point and return governance decision."""
        enriched = dict(payload)
        enriched.setdefault("phase", phase.value)
        enriched.setdefault("context_id", self._context.id)
        if self._conversation_id:
            enriched.setdefault("conversation_id", self._conversation_id)
        if self._session_state:
            enriched.setdefault("task_id", self._session_state.task_id)
            enriched.setdefault("run_id", self._session_state.run_id)
            enriched.setdefault("session_id", self._session_state.run_id)
        if self._extension_point is not None:
            try:
                return await self._extension_point.emit(phase, enriched)
            except Exception:
                return HookResult(decision=HookDecision.ALLOW)
        return HookResult(decision=HookDecision.ALLOW)

    def _record_token_usage(self, usage: dict[str, Any] | None) -> None:
        if not usage:
            return

        def _safe_int(value: Any) -> int:
            try:
                return int(value or 0)
            except (TypeError, ValueError):
                return 0

        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
        cached_tokens = usage.get("cached_tokens", 0)
        parsed_input_tokens = _safe_int(input_tokens)
        parsed_output_tokens = _safe_int(output_tokens)
        parsed_cached_tokens = _safe_int(cached_tokens)
        self._token_usage["input_tokens"] += parsed_input_tokens
        self._token_usage["output_tokens"] += parsed_output_tokens
        self._token_usage["cached_tokens"] += parsed_cached_tokens

        # Some adapters only report total_tokens; keep that signal so output envelope usage is not dropped.
        total_tokens = usage.get("total_tokens")
        parsed_total_tokens = _safe_int(total_tokens)
        if total_tokens is None or (
            parsed_total_tokens == 0 and (parsed_input_tokens or parsed_output_tokens)
        ):
            parsed_total_tokens = parsed_input_tokens + parsed_output_tokens
        self._token_usage["total_tokens"] += parsed_total_tokens

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

    def _with_output_envelope(self, result: RunResult) -> RunResult:
        usage = self._run_usage_summary()
        output = build_output_envelope(
            result.output,
            metadata=result.metadata,
            usage=usage,
        )
        return replace(result, output=output, output_text=output["content"])

    def _run_usage_summary(self) -> dict[str, Any] | None:
        input_tokens = self._token_usage.get("input_tokens", 0)
        output_tokens = self._token_usage.get("output_tokens", 0)
        cached_tokens = self._token_usage.get("cached_tokens", 0)
        total_tokens = self._token_usage.get("total_tokens", input_tokens + output_tokens)
        if not any((input_tokens, output_tokens, cached_tokens, total_tokens)):
            return None
        summary: dict[str, Any] = {"total_tokens": total_tokens}
        if input_tokens:
            summary["input_tokens"] = input_tokens
        if output_tokens:
            summary["output_tokens"] = output_tokens
        if cached_tokens:
            summary["cached_tokens"] = cached_tokens
        return summary

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
        if self._conversation_id:
            payload = {
                "conversation_id": self._conversation_id,
                **payload,
            }
        if self._session_state:
            payload = {
                "task_id": self._session_state.task_id,
                "run_id": self._session_state.run_id,
                "session_id": self._session_state.run_id,
                **payload,
            }

        if self._event_log is not None:
            try:
                await self._event_log.append(event_type, payload)
            except Exception as exc:  # pragma: no cover - exercised via tests
                self._logger.exception("event log append failed: %s", event_type)
                raise EventLogWriteError(
                    f"event log append failed for {event_type}: {exc}"
                ) from exc

    def _extract_conversation_id(self, task: Task) -> str | None:
        metadata_sources = [task.metadata if isinstance(task.metadata, dict) else {}]
        if task.input_message is not None and isinstance(task.input_message.metadata, dict):
            metadata_sources.append(task.input_message.metadata)
        for metadata in metadata_sources:
            for key in ("conversation_id", "session_id"):
                candidate = metadata.get(key)
                if isinstance(candidate, str):
                    normalized = candidate.strip()
                    if normalized:
                        return normalized
        return None


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


__all__ = ["DareAgent", "EventLogWriteError"]
