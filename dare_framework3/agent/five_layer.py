"""FiveLayerAgent - Five-layer loop execution strategy.

Implements the Session -> Milestone -> Plan -> Execute -> Tool loop pattern.
This is the primary agent implementation for complex task orchestration.

The five-layer loop provides:
- Session loop: Manages full task lifecycle, breaks into milestones
- Milestone loop: Executes milestones with retry/remediation
- Plan loop: Generates and validates plans for milestones
- Execute loop: Executes validated plan steps (or model-driven tool calling)
- Tool loop: Executes individual tool calls within envelope constraints

Migrated from DefaultLoopOrchestrator in dare_framework2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from dare_framework3.agent.base import BaseAgent
from dare_framework3.context.types import ContextStage, RuntimeStateView
from dare_framework3.model.types import Message
from dare_framework3.plan.types import (
    Task,
    Milestone,
    ValidatedPlan,
    ToolLoopRequest,
    Envelope,
    DonePredicate,
    RunResult,
    MilestoneResult,
    MilestoneSummary,
    SessionSummary,
    ExecuteResult,
    VerifyResult,
    ToolLoopResult,
)
from dare_framework3.runtime.types import ResourceType, HookPhase
from dare_framework3.tool.types import (
    RiskLevel,
    ToolDefinition,
    ToolResult,
    ToolType,
    CapabilityType,
    PolicyDecision,
    SandboxSpec,
)

if TYPE_CHECKING:
    from dare_framework3.config.types import Config
    from dare_framework3.memory.interfaces import IMemory
    from dare_framework3.model.interfaces import IModelAdapter
    from dare_framework3.plan.interfaces import IPlanner, IValidator, IRemediator
    from dare_framework3.runtime.interfaces import IHook
    from dare_framework3.runtime.types import Budget
    from dare_framework3.tool.interfaces import ITool, IProtocolAdapter


@dataclass
class _MilestoneState:
    """Internal milestone state holder for plan isolation and verification."""
    milestone: Milestone
    reflections: list[str] = field(default_factory=list)
    attempted_plans: list[dict[str, Any]] = field(default_factory=list)
    evidence_collected: list[Any] = field(default_factory=list)

    def add_reflection(self, text: str) -> None:
        self.reflections.append(text)

    def add_attempt(self, attempt: dict[str, Any]) -> None:
        self.attempted_plans.append(attempt)


class FiveLayerAgent(BaseAgent):
    """Five-layer loop agent implementation.
    
    Executes tasks using the Session -> Milestone -> Plan -> Execute -> Tool loop.
    
    This agent is suitable for:
    - Complex multi-step tasks
    - Tasks requiring planning and validation
    - Tasks with retry/remediation requirements
    - Tasks needing human-in-the-loop approval
    
    Example:
        agent = FiveLayerAgent(
            name="my-agent",
            model=model,
            tools=[tool1, tool2],
        )
        result = await agent.run("Complete the given task")
    """

    def __init__(
        self,
        name: str,
        *,
        model: "IModelAdapter | None" = None,
        tools: list["ITool"] | None = None,
        protocol_adapters: list["IProtocolAdapter"] | None = None,
        planner: "IPlanner | None" = None,
        validator: "IValidator | None" = None,
        remediator: "IRemediator | None" = None,
        memory: "IMemory | None" = None,
        hooks: list["IHook"] | None = None,
        budget: "Budget | None" = None,
        config: "Config | None" = None,
    ) -> None:
        super().__init__(
            name,
            model=model,
            tools=tools,
            protocol_adapters=protocol_adapters,
            planner=planner,
            validator=validator,
            remediator=remediator,
            memory=memory,
            hooks=hooks,
            budget=budget,
            config=config,
        )
        # Internal state for current execution
        self._task: Task | None = None
        self._run_id: str | None = None
        self._milestone_state: _MilestoneState | None = None

    async def _execute(self, task: Task) -> RunResult:
        """Execute task using five-layer loop strategy."""
        return await self._run_session_loop(task)

    # =========================================================================
    # Five-Layer Loop Implementation
    # =========================================================================

    async def _run_session_loop(self, task: Task) -> RunResult:
        """Run the session loop for a task.
        
        The outermost loop that manages the full task lifecycle.
        Breaks the task into milestones and executes them sequentially.
        """
        self._task = task
        self._run_id = uuid4().hex
        if self._run_context_state is not None:
            self._run_context_state.run_id = self._run_id
            self._run_context_state.task_id = task.task_id

        await self._log_event("session.start", {
            "task_id": task.task_id,
            "run_id": self._run_id,
        })

        milestone_results: list[MilestoneResult] = []
        errors: list[str] = []

        # Execute milestones sequentially
        for milestone in task.to_milestones():
            result = await self._run_milestone_loop(milestone)
            milestone_results.append(result)
            if not result.success:
                errors.extend(result.errors or ["milestone failed"])
                break

        success = not errors
        session_summary = SessionSummary(
            session_id=f"session_{task.task_id}",
            milestone_count=len(milestone_results),
            success=success,
        )
        await self._log_event("session.complete", {
            "task_id": task.task_id,
            "run_id": self._run_id,
            "success": success,
        })
        
        output = milestone_results[-1].outputs if milestone_results else None
        return RunResult(
            success=success,
            output=output,
            milestone_results=milestone_results,
            errors=errors,
            session_summary=session_summary,
        )

    async def _run_milestone_loop(self, milestone: Milestone) -> MilestoneResult:
        """Run the milestone loop.
        
        Executes a single milestone with retry/remediation support.
        Attempts planning and execution up to max_attempts times.
        """
        if self._task is None or self._run_id is None:
            raise RuntimeError("_run_session_loop must be called first")

        if self._run_context_state is not None:
            self._run_context_state.milestone_id = milestone.milestone_id

        self._milestone_state = _MilestoneState(milestone=milestone)
        await self._log_event("milestone.start", {
            "task_id": self._task.task_id,
            "run_id": self._run_id,
            "milestone_id": milestone.milestone_id,
        })

        max_attempts = 3
        for attempt in range(max_attempts):
            # Plan loop: generate and validate plan
            validated = await self._run_plan_loop(milestone)
            if not validated.success:
                self._milestone_state.add_attempt({
                    "attempt": attempt,
                    "errors": list(validated.errors),
                })
                # Remediate and retry
                reflection = await self._remediator.remediate(
                    VerifyResult(success=False, errors=list(validated.errors), evidence=[]),
                    ctx=self._state_dict(stage=ContextStage.PLAN),
                )
                self._milestone_state.add_reflection(reflection)
                continue

            # Check if human approval is needed
            await self._maybe_human_approval(validated)

            # Execute loop: execute the validated plan
            execute_result = await self._run_execute_loop(validated)
            if execute_result.encountered_plan_tool:
                self._milestone_state.add_reflection(
                    f"plan tool encountered: {execute_result.plan_tool_name or 'unknown'}"
                )
                continue

            # Verify milestone completion
            verify = await self._validator.verify_milestone(
                execute_result,
                ctx=self._state_dict(stage=ContextStage.VERIFY),
            )
            if verify.success:
                await self._log_event("milestone.success", {
                    "task_id": self._task.task_id,
                    "run_id": self._run_id,
                    "milestone_id": milestone.milestone_id,
                })
                summary = MilestoneSummary(
                    milestone_id=milestone.milestone_id,
                    description=milestone.description,
                    success=True,
                    attempt_count=attempt + 1,
                    evidence_count=len(self._milestone_state.evidence_collected),
                )
                return MilestoneResult(
                    success=True,
                    outputs=execute_result.outputs,
                    errors=[],
                    verify_result=verify,
                    summary=summary,
                )

            # Remediate verification failure
            reflection = await self._remediator.remediate(
                verify,
                ctx=self._state_dict(stage=ContextStage.VERIFY),
            )
            self._milestone_state.add_reflection(reflection)

        # All attempts exhausted
        await self._log_event("milestone.failed", {
            "task_id": self._task.task_id,
            "run_id": self._run_id,
            "milestone_id": milestone.milestone_id,
        })
        summary = MilestoneSummary(
            milestone_id=milestone.milestone_id,
            description=milestone.description,
            success=False,
            attempt_count=len(self._milestone_state.attempted_plans),
            evidence_count=len(self._milestone_state.evidence_collected),
        )
        return MilestoneResult(
            success=False,
            outputs=[],
            errors=["milestone failed"],
            verify_result=None,
            summary=summary,
        )

    async def _run_plan_loop(self, milestone: Milestone) -> ValidatedPlan:
        """Run the plan loop.
        
        Generates and validates a plan for a milestone.
        """
        self._execution_control.poll_or_raise()
        self._resource_manager.check_limit(scope="plan")

        if self._extension_point is not None:
            await self._extension_point.emit(HookPhase.BEFORE_PLAN, {
                "milestone_id": milestone.milestone_id,
                "run_id": self._run_id,
            })

        # Assemble context and generate plan
        assembled = await self._context_manager.assemble(
            ContextStage.PLAN,
            self._runtime_state(stage=ContextStage.PLAN),
        )
        proposed = await self._planner.plan(assembled)
        await self._log_event("plan.attempt", {
            "task_id": self._task.task_id if self._task else None,
            "run_id": self._run_id,
            "milestone_id": milestone.milestone_id,
            "attempt": proposed.attempt,
            "plan_description": proposed.plan_description,
            "steps": [step.capability_id for step in proposed.steps],
        })

        # Validate the proposed plan
        validated = await self._validator.validate_plan(
            proposed,
            ctx=self._state_dict(stage=ContextStage.PLAN),
        )
        if validated.success:
            await self._log_event("plan.validated", {
                "task_id": self._task.task_id if self._task else None,
                "run_id": self._run_id,
                "milestone_id": milestone.milestone_id,
                "plan_description": validated.plan_description,
                "steps": [step.capability_id for step in validated.steps],
            })
        else:
            await self._log_event("plan.invalid", {
                "task_id": self._task.task_id if self._task else None,
                "run_id": self._run_id,
                "milestone_id": milestone.milestone_id,
                "errors": list(validated.errors),
                "plan_description": validated.plan_description,
            })

        if self._extension_point is not None:
            await self._extension_point.emit(HookPhase.AFTER_PLAN, {
                "milestone_id": milestone.milestone_id,
                "run_id": self._run_id,
            })
        return validated

    async def _run_execute_loop(self, plan: ValidatedPlan) -> ExecuteResult:
        """Run the execute loop.
        
        Executes validated plan steps, either step-by-step or model-driven.
        """
        self._execution_control.poll_or_raise()
        self._resource_manager.check_limit(scope="execute")
        
        # If no model adapter, execute plan steps directly
        if self._model is None:
            return await self._execute_validated_plan(plan)
        
        # Otherwise use model-driven execution
        return await self._execute_model_driven()

    async def _run_tool_loop(self, req: ToolLoopRequest) -> ToolLoopResult:
        """Run the tool loop.
        
        Executes a tool within its envelope constraints.
        Handles security checks, policy enforcement, and retries.
        """
        capability_id = req.capability_id
        if not capability_id:
            raise ValueError("ToolLoopRequest.capability_id is required")

        envelope = req.envelope
        max_calls = envelope.budget.max_tool_calls or 1
        last_result = ToolResult(
            success=False,
            output={},
            error="tool loop not executed",
            evidence=[],
        )

        for attempt in range(int(max_calls)):
            self._execution_control.poll_or_raise()
            self._resource_manager.check_limit(scope="tool")
            self._resource_manager.acquire(ResourceType.TOOL_CALLS, 1, scope="tool")

            # Security checks
            context = await self._capability_context(capability_id)
            trusted = await self._security_boundary.verify_trust(input=req.params, context=context)
            decision = await self._security_boundary.check_policy(
                action="invoke_capability",
                resource=capability_id,
                context={**context, "risk_level": trusted.risk_level},
            )
            await self._log_event("policy.decision", {
                "task_id": self._task.task_id if self._task else None,
                "run_id": self._run_id,
                "milestone_id": self._milestone_state.milestone.milestone_id if self._milestone_state else None,
                "action": "invoke_capability",
                "resource": capability_id,
                "decision": decision.value,
            })
            
            if decision == PolicyDecision.DENY:
                return ToolLoopResult(success=False, result=last_result, attempts=attempt + 1)
            if decision == PolicyDecision.APPROVE_REQUIRED:
                checkpoint_id = await self._execution_control.pause("tool_approval_required")
                await self._execution_control.wait_for_human(checkpoint_id, "tool_approval_required")
                await self._execution_control.resume(checkpoint_id)

            # Emit before-tool hook
            if self._extension_point is not None:
                await self._extension_point.emit(HookPhase.BEFORE_TOOL, {
                    "capability_id": capability_id,
                    "run_id": self._run_id,
                    "attempt": attempt,
                })

            await self._log_event("tool.invoke", {
                "task_id": self._task.task_id if self._task else None,
                "run_id": self._run_id,
                "milestone_id": self._milestone_state.milestone.milestone_id if self._milestone_state else None,
                "capability_id": capability_id,
                "params": trusted.params,
            })
            
            # Execute tool in sandbox
            result: ToolResult = await self._security_boundary.execute_safe(
                action="invoke_capability",
                fn=lambda: self._tool_gateway.invoke(capability_id, trusted.params, envelope=envelope),
                sandbox=SandboxSpec(mode="stub"),
            )
            last_result = result
            
            await self._log_event("tool.result", {
                "task_id": self._task.task_id if self._task else None,
                "run_id": self._run_id,
                "milestone_id": self._milestone_state.milestone.milestone_id if self._milestone_state else None,
                "capability_id": capability_id,
                "success": result.success,
                "error": result.error,
            })
            
            # Collect evidence
            if self._milestone_state is not None:
                self._milestone_state.evidence_collected.extend(result.evidence)

            # Emit after-tool hook
            if self._extension_point is not None:
                await self._extension_point.emit(HookPhase.AFTER_TOOL, {
                    "capability_id": capability_id,
                    "run_id": self._run_id,
                    "attempt": attempt,
                    "success": result.success,
                })

            if not result.success:
                continue

            # Check if done predicate is satisfied
            if _done_predicate_satisfied(result.evidence, envelope.done_predicate):
                return ToolLoopResult(success=True, result=result, attempts=attempt + 1)

        return ToolLoopResult(success=False, result=last_result, attempts=int(max_calls))

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _execute_validated_plan(self, plan: ValidatedPlan) -> ExecuteResult:
        """Execute a validated plan step by step."""
        outputs: list[ToolResult] = []
        errors: list[str] = []

        for step in plan.steps:
            self._execution_control.poll_or_raise()
            self._resource_manager.check_limit(scope="execute")
            
            # Check for plan-tool (indicates need for re-planning)
            if step.capability_id.startswith("plan:"):
                await self._log_event("plan.tool_encountered", {
                    "task_id": self._task.task_id if self._task else None,
                    "run_id": self._run_id,
                    "milestone_id": self._milestone_state.milestone.milestone_id if self._milestone_state else None,
                    "capability_id": step.capability_id,
                    "step_id": step.step_id,
                })
                return ExecuteResult(
                    success=False,
                    outputs=outputs,
                    errors=errors,
                    encountered_plan_tool=True,
                    plan_tool_name=step.capability_id,
                )

            # Build execution envelope
            boundary = step.envelope or Envelope()
            boundary = Envelope(
                allowed_capability_ids=boundary.allowed_capability_ids or [step.capability_id],
                budget=boundary.budget,
                done_predicate=boundary.done_predicate,
                risk_level=step.risk_level,
            )
            
            # Execute tool loop
            loop_result = await self._run_tool_loop(
                ToolLoopRequest(
                    capability_id=step.capability_id,
                    params=dict(step.params),
                    envelope=boundary,
                )
            )
            outputs.append(loop_result.result)
            if not loop_result.success:
                errors.append(loop_result.result.error or "tool loop failed")
                return ExecuteResult(success=False, outputs=outputs, errors=errors)

        return ExecuteResult(success=not errors, outputs=outputs, errors=errors)

    async def _execute_model_driven(self) -> ExecuteResult:
        """Execute using model-driven tool calling."""
        if self._task is None or self._milestone_state is None or self._run_id is None:
            raise RuntimeError("_run_session_loop must be called first")

        assembled = await self._context_manager.assemble(
            ContextStage.EXECUTE,
            self._runtime_state(stage=ContextStage.EXECUTE),
        )
        messages = list(assembled.messages)
        tools = await self._tool_definitions_for_model()
        tool_index = {tool.name: tool for tool in tools}

        outputs: list[ToolResult] = []
        errors: list[str] = []
        
        # Model-driven loop with max iterations
        for _ in range(20):
            self._execution_control.poll_or_raise()
            self._resource_manager.check_limit(scope="execute")
            
            response = await self._model.generate(messages, tools)
            await self._log_event("model.response", {
                "task_id": self._task.task_id,
                "run_id": self._run_id,
                "milestone_id": self._milestone_state.milestone.milestone_id,
                "content": response.content,
                "tool_calls": response.tool_calls,
            })
            
            # No tool calls means model is done
            if not response.tool_calls:
                outputs.append(ToolResult(
                    success=True,
                    output={"content": response.content},
                    evidence=[],
                ))
                return ExecuteResult(success=True, outputs=outputs, errors=errors)

            messages.append(Message(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
            ))
            
            # Process each tool call
            for tool_call in response.tool_calls:
                name = tool_call.get("name")
                if not isinstance(name, str) or not name:
                    errors.append("model returned tool call without name")
                    return ExecuteResult(success=False, outputs=outputs, errors=errors)
                
                # Check for plan-tool
                if name.startswith("plan:"):
                    return ExecuteResult(
                        success=False,
                        outputs=outputs,
                        errors=errors,
                        encountered_plan_tool=True,
                        plan_tool_name=name,
                    )
                
                # Parse tool arguments
                args = tool_call.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        errors.append(f"invalid tool arguments for {name}")
                        return ExecuteResult(success=False, outputs=outputs, errors=errors)
                if not isinstance(args, dict):
                    errors.append(f"invalid tool arguments type for {name}")
                    return ExecuteResult(success=False, outputs=outputs, errors=errors)

                tool_def = tool_index.get(name)
                if tool_def is None:
                    errors.append(f"model requested unknown tool: {name}")
                    return ExecuteResult(success=False, outputs=outputs, errors=errors)

                # Execute tool
                boundary = Envelope(
                    allowed_capability_ids=[name],
                    risk_level=tool_def.risk_level,
                )
                loop_result = await self._run_tool_loop(
                    ToolLoopRequest(
                        capability_id=name,
                        params=args,
                        envelope=boundary,
                    )
                )
                outputs.append(loop_result.result)
                if not loop_result.success:
                    errors.append(loop_result.result.error or "tool failed")
                    return ExecuteResult(success=False, outputs=outputs, errors=errors)

                # Add tool result to messages
                tool_content = json.dumps({
                    "capability_id": name,
                    "output": loop_result.result.output,
                    "error": loop_result.result.error,
                })
                messages.append(Message(
                    role="tool",
                    content=tool_content,
                    name=name,
                    tool_call_id=tool_call.get("id"),
                ))

        errors.append("model tool loop exceeded max iterations")
        return ExecuteResult(success=False, outputs=outputs, errors=errors)

    async def _maybe_human_approval(self, plan: ValidatedPlan) -> None:
        """Check if human approval is needed for the plan."""
        plan_risk = _max_risk([step.risk_level for step in plan.steps])
        decision = await self._security_boundary.check_policy(
            action="execute_plan",
            resource=plan.plan_description,
            context={"risk_level": plan_risk},
        )
        await self._log_event("policy.decision", {
            "task_id": self._task.task_id if self._task else None,
            "run_id": self._run_id,
            "milestone_id": self._milestone_state.milestone.milestone_id if self._milestone_state else None,
            "action": "execute_plan",
            "resource": plan.plan_description,
            "decision": decision.value,
        })
        if decision == PolicyDecision.APPROVE_REQUIRED:
            checkpoint_id = await self._execution_control.pause("hitl_approval_required")
            await self._execution_control.wait_for_human(checkpoint_id, "hitl_approval_required")
            await self._execution_control.resume(checkpoint_id)

    async def _tool_definitions_for_model(self) -> list[ToolDefinition]:
        """Get tool definitions for model consumption."""
        tool_defs: list[ToolDefinition] = []
        for cap in await self._tool_gateway.list_capabilities():
            if cap.type != CapabilityType.TOOL:
                continue
            meta = cap.metadata or {}
            tool_type = ToolType.WORKUNIT if meta.get("is_work_unit") else ToolType.ATOMIC
            tool_defs.append(
                ToolDefinition(
                    name=cap.id,
                    description=cap.description,
                    input_schema=dict(cap.input_schema),
                    output_schema=dict(cap.output_schema or {}),
                    tool_type=tool_type,
                    risk_level=_parse_risk_level(meta.get("risk_level")),
                    requires_approval=bool(meta.get("requires_approval", False)),
                    timeout_seconds=int(meta.get("timeout_seconds", 30)),
                    produces_assertions=[],
                    is_work_unit=bool(meta.get("is_work_unit", False)),
                )
            )
        return tool_defs

    async def _capability_context(self, capability_id: str) -> dict[str, Any]:
        """Get security context for a capability."""
        # Fail-closed: unknown capabilities require approval
        risk_level = RiskLevel.NON_IDEMPOTENT_EFFECT
        requires_approval = True
        for cap in await self._tool_gateway.list_capabilities():
            if cap.id == capability_id:
                meta = cap.metadata or {}
                risk_level = _parse_risk_level(meta.get("risk_level"))
                requires_approval = bool(meta.get("requires_approval", False))
                break
        return {
            "task_id": self._task.task_id if self._task else None,
            "run_id": self._run_id,
            "milestone_id": self._milestone_state.milestone.milestone_id if self._milestone_state else None,
            "risk_level": risk_level,
            "requires_approval": requires_approval,
        }

    def _runtime_state(self, *, stage: ContextStage) -> RuntimeStateView:
        """Build runtime state view for context assembly."""
        if self._task is None or self._run_id is None:
            raise RuntimeError("Task and run_id must be set")
        milestone_id = self._milestone_state.milestone.milestone_id if self._milestone_state else None
        return RuntimeStateView(
            task_id=self._task.task_id,
            run_id=self._run_id,
            milestone_id=milestone_id,
            stage=stage,
            data={
                "task_description": self._task.description,
                "milestone_description": self._milestone_state.milestone.description if self._milestone_state else None,
                "user_input": self._milestone_state.milestone.user_input if self._milestone_state else self._task.description,
                "reflections": list(self._milestone_state.reflections) if self._milestone_state else [],
                "attempted_plans": list(self._milestone_state.attempted_plans) if self._milestone_state else [],
            },
        )

    def _state_dict(self, *, stage: ContextStage) -> dict[str, Any]:
        """Build state dictionary for validators/remediators."""
        if self._task is None or self._run_id is None:
            return {}
        milestone_id = self._milestone_state.milestone.milestone_id if self._milestone_state else None
        return {
            "task_id": self._task.task_id,
            "run_id": self._run_id,
            "milestone_id": milestone_id,
            "stage": stage.value,
            "task_description": self._task.description,
            "milestone_description": self._milestone_state.milestone.description if self._milestone_state else None,
            "reflections": list(self._milestone_state.reflections) if self._milestone_state else [],
            "attempted_plans": list(self._milestone_state.attempted_plans) if self._milestone_state else [],
        }

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Log an event to the event log."""
        await self._event_log.append(event_type, payload)


# =============================================================================
# Utility Functions
# =============================================================================

def _done_predicate_satisfied(evidence: list[Any], predicate: DonePredicate | None) -> bool:
    """Check if the done predicate is satisfied."""
    if predicate is None:
        return True
    if not predicate.required_keys and not predicate.evidence_conditions:
        return True
    if predicate.required_keys:
        available_keys: set[str] = set()
        for item in evidence:
            payload = getattr(item, "payload", None)
            if isinstance(payload, dict):
                available_keys.update(payload.keys())
        if not set(predicate.required_keys).issubset(available_keys):
            return False
    if predicate.evidence_conditions:
        checks = [condition.check(evidence) for condition in predicate.evidence_conditions]
        return all(checks) if predicate.require_all else any(checks)
    return True


def _parse_risk_level(value: object) -> RiskLevel:
    """Parse a risk level from various input types."""
    if isinstance(value, RiskLevel):
        return value
    if isinstance(value, str):
        try:
            return RiskLevel(value)
        except ValueError:
            return RiskLevel.READ_ONLY
    return RiskLevel.READ_ONLY


def _max_risk(levels: list[RiskLevel]) -> RiskLevel:
    """Get the maximum risk level from a list."""
    if not levels:
        return RiskLevel.READ_ONLY
    order = {
        RiskLevel.READ_ONLY: 0,
        RiskLevel.IDEMPOTENT_WRITE: 1,
        RiskLevel.COMPENSATABLE: 2,
        RiskLevel.NON_IDEMPOTENT_EFFECT: 3,
    }
    return max(levels, key=lambda level: order.get(level, 0))
