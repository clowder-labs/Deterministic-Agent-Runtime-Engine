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
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

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
from dare_framework.plan.types import Envelope, Milestone, RunResult, Task, ToolLoopRequest, ValidatedPlan, VerifyResult
from dare_framework.tool._internal.governed_tool_gateway import (
    GovernedToolGateway,
)
from dare_framework.tool.types import CapabilityKind


if TYPE_CHECKING:
    from dare_framework.config.types import Config
    from dare_framework.context.kernel import IContext
    from dare_framework.event.kernel import IEventLog
    from dare_framework.hook.kernel import IHook
    from dare_framework.mcp.manager import MCPManager
    from dare_framework.observability.kernel import ITelemetryProvider
    from dare_framework.plan.interfaces import IPlanner, IRemediator, IValidator
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
            approval_manager: Tool approval manager for persisted approval memory (optional).
            planner: Plan generator (optional, enables full five-layer).
            validator: Plan/milestone validator (optional).
            remediator: Failure remediator (optional).
            event_log: Event log for audit (optional).
            hooks: Hook implementations invoked at lifecycle phases (optional).
            telemetry: Telemetry provider for traces/metrics/logs (optional).
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
        self._conversation_id: str | None = None
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
        task: str | Task,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Execute a task with automatic mode selection."""
        previous_conversation_id = self._conversation_id
        if isinstance(task, Task):
            task_obj = task
        else:
            task_obj = Task(
                description=task,
                task_id=uuid4().hex[:8],
            )
        self._conversation_id = self._extract_conversation_id(task_obj)
        start_time = time.perf_counter()
        if task_obj.task_id is None:
            task_obj = replace(task_obj, task_id=uuid4().hex[:8])
        self._session_state = SessionState(task_id=task_obj.task_id)
        self._token_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
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
    ) -> dict[str, Any]:
        """Run the tool loop - single tool invocation."""
        return await run_tool_loop(
            self,
            request,
            transport=transport,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            descriptor=descriptor,
        )

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
                message.content,
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
        if self._conversation_id:
            payload = {
                "conversation_id": self._conversation_id,
                **payload,
            }
        if self._session_state:
            payload = {
                "task_id": self._session_state.task_id,
                "run_id": self._session_state.run_id,
                **payload,
            }

        if self._event_log is not None:
            await self._event_log.append(event_type, payload)

    def _extract_conversation_id(self, task: Task) -> str | None:
        metadata = task.metadata if isinstance(task.metadata, dict) else {}
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


__all__ = ["DareAgent"]
