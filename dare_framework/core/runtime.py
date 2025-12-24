from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from uuid import uuid4

from ..components.checkpoint import FileCheckpoint
from ..components.context_assembler import BasicContextAssembler
from ..components.event_log import LocalEventLog
from ..components.policy_engine import AllowAllPolicyEngine
from ..components.remediator import NoOpRemediator
from ..components.validator import SimpleValidator
from .interfaces import (
    ICheckpoint,
    IContextAssembler,
    IEventLog,
    IPlanGenerator,
    IPolicyEngine,
    IRemediator,
    IRuntime,
    IToolRuntime,
    IValidator,
)
from .models import (
    Event,
    ExecuteResult,
    Milestone,
    MilestoneContext,
    MilestoneResult,
    MilestoneSummary,
    PlanBudget,
    ProposedPlan,
    ProposedStep,
    RiskLevel,
    RunContext,
    RunResult,
    RuntimeSnapshot,
    RuntimeState,
    SessionContext,
    SessionSummary,
    StepType,
    Task,
    ToolErrorRecord,
    ValidatedPlan,
    ValidatedStep,
    VerifyResult,
    new_id,
)

DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")


@dataclass
class PlanLoopOutcome:
    validated_plan: ValidatedPlan | None
    reflection: str | None
    errors: list[str]


class AgentRuntime(IRuntime[DepsT, OutputT], Generic[DepsT, OutputT]):
    def __init__(
        self,
        tool_runtime: IToolRuntime,
        plan_generator: IPlanGenerator,
        validator: IValidator | None = None,
        policy_engine: IPolicyEngine | None = None,
        remediator: IRemediator | None = None,
        context_assembler: IContextAssembler | None = None,
        event_log: IEventLog | None = None,
        checkpoint: ICheckpoint | None = None,
    ) -> None:
        self._tool_runtime = tool_runtime
        self._plan_generator = plan_generator
        self._validator = validator or SimpleValidator()
        self._policy_engine = policy_engine or AllowAllPolicyEngine()
        self._remediator = remediator or NoOpRemediator()
        self._context_assembler = context_assembler or BasicContextAssembler()
        self._event_log = event_log or LocalEventLog()
        self._checkpoint = checkpoint or FileCheckpoint()
        self._state = RuntimeState.READY
        self._active_task: Task | None = None
        self._run_id: str | None = None

    async def init(self, task: Task) -> None:
        self._active_task = task
        self._state = RuntimeState.READY
        await self._log_event("runtime.init", {"task_id": task.task_id})

    async def run(self, task: Task, deps: DepsT) -> RunResult[OutputT]:
        if self._state not in {RuntimeState.READY, RuntimeState.PAUSED}:
            raise RuntimeError(f"Runtime state invalid for run: {self._state}")
        if self._active_task is None or self._active_task.task_id != task.task_id:
            self._active_task = task
        self._state = RuntimeState.RUNNING
        self._run_id = uuid4().hex
        await self._log_event("runtime.run", {"task_id": task.task_id, "run_id": self._run_id})

        previous_summary = None
        if isinstance(task.context.get("previous_session_summary"), SessionSummary):
            previous_summary = task.context.get("previous_session_summary")

        session_ctx = SessionContext(
            user_input=task.description,
            previous_session_summary=previous_summary,
        )

        milestone_results: list[MilestoneResult] = []
        errors: list[str] = []
        for milestone in task.to_milestones():
            ctx = RunContext(
                deps=deps,
                run_id=self._run_id,
                task_id=task.task_id,
                milestone_id=milestone.milestone_id,
            )
            milestone_ctx = MilestoneContext(
                user_input=milestone.user_input,
                milestone_description=milestone.description,
            )
            result = await self._milestone_loop(milestone, milestone_ctx, ctx)
            milestone_results.append(result)
            if result.summary:
                session_ctx.milestone_summaries.append(result.summary)
            if not result.success:
                errors.extend(result.errors)
                break

        success = not errors
        output = milestone_results[-1].outputs if milestone_results else None
        session_summary = SessionSummary(
            session_id=f"session_{task.task_id}",
            milestone_count=len(session_ctx.milestone_summaries),
            success=success,
        )
        await self._log_event(
            "runtime.complete",
            {"task_id": task.task_id, "run_id": self._run_id, "success": success},
        )
        self._state = RuntimeState.STOPPED if success else RuntimeState.CANCELLED
        return RunResult(
            success=success,
            output=output,
            milestone_results=milestone_results,
            errors=errors,
            session_summary=session_summary,
        )

    async def pause(self) -> None:
        if self._state != RuntimeState.RUNNING:
            return
        snapshot = RuntimeSnapshot(
            state=self._state,
            task_id=self._active_task.task_id if self._active_task else "",
            milestone_id=None,
        )
        checkpoint_id = await self._checkpoint.save(snapshot)
        await self._log_event("runtime.pause", {"checkpoint_id": checkpoint_id})
        self._state = RuntimeState.PAUSED

    async def resume(self) -> None:
        if self._state != RuntimeState.PAUSED:
            return
        self._state = RuntimeState.RUNNING
        await self._log_event("runtime.resume", {"task_id": self._active_task.task_id if self._active_task else ""})

    async def stop(self) -> None:
        self._state = RuntimeState.STOPPED
        await self._log_event("runtime.stop", {"task_id": self._active_task.task_id if self._active_task else ""})

    async def cancel(self) -> None:
        self._state = RuntimeState.CANCELLED
        await self._log_event("runtime.cancel", {"task_id": self._active_task.task_id if self._active_task else ""})

    def get_state(self) -> RuntimeState:
        return self._state

    async def _milestone_loop(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> MilestoneResult:
        await self._log_event(
            "milestone.start",
            {"milestone_id": milestone.milestone_id, "run_id": ctx.run_id},
        )
        plan_budget = PlanBudget()
        for attempt in range(plan_budget.max_attempts):
            plan_outcome = await self._plan_loop(milestone, milestone_ctx, ctx)
            if not plan_outcome.validated_plan:
                milestone_ctx.add_reflection(plan_outcome.reflection or "plan failed")
                milestone_ctx.add_attempt({"attempt": attempt, "errors": plan_outcome.errors})
                continue

            if self._policy_engine.needs_approval(milestone, plan_outcome.validated_plan):
                await self.pause()
                await self.resume()

            execute_result = await self._execute_loop(plan_outcome.validated_plan, milestone_ctx, ctx)
            if execute_result.encountered_plan_tool:
                milestone_ctx.add_reflection(f"plan tool encountered: {execute_result.plan_tool_name}")
                continue

            verify_result = await self._validator.validate_milestone(milestone, execute_result, ctx)
            if verify_result.success:
                await self._log_event(
                    "milestone.success",
                    {"milestone_id": milestone.milestone_id, "run_id": ctx.run_id},
                )
                summary = MilestoneSummary(
                    milestone_id=milestone.milestone_id,
                    description=milestone.description,
                    success=True,
                    attempt_count=len(milestone_ctx.attempted_plans) + 1,
                    evidence_count=len(milestone_ctx.evidence_collected),
                )
                return MilestoneResult(
                    success=True,
                    outputs=execute_result.outputs,
                    errors=[],
                    verify_result=verify_result,
                    summary=summary,
                )

            reflection = await self._remediator.remediate(
                verify_result,
                milestone_ctx.tool_errors,
                milestone_ctx,
                ctx,
            )
            milestone_ctx.add_reflection(reflection)

        await self._log_event(
            "milestone.failed",
            {"milestone_id": milestone.milestone_id, "run_id": ctx.run_id},
        )
        summary = MilestoneSummary(
            milestone_id=milestone.milestone_id,
            description=milestone.description,
            success=False,
            attempt_count=len(milestone_ctx.attempted_plans),
            evidence_count=len(milestone_ctx.evidence_collected),
        )
        return MilestoneResult(
            success=False,
            outputs=[],
            errors=["milestone failed"],
            verify_result=None,
            summary=summary,
        )

    async def _plan_loop(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> PlanLoopOutcome:
        assembled = await self._context_assembler.assemble(milestone, milestone_ctx, ctx)
        ctx.metadata["context_messages"] = assembled.messages
        proposed_plan = await self._plan_generator.generate_plan(
            milestone,
            milestone_ctx,
            milestone_ctx.attempted_plans,
            ctx,
        )
        await self._log_event(
            "plan.attempt",
            {"milestone_id": milestone.milestone_id, "attempt": proposed_plan.attempt, "run_id": ctx.run_id},
        )
        validation = await self._validator.validate_plan(proposed_plan.proposed_steps, ctx)
        if validation.success:
            await self._log_event(
                "plan.validated",
                {"milestone_id": milestone.milestone_id, "run_id": ctx.run_id},
            )
            validated = self._build_validated_plan(proposed_plan)
            return PlanLoopOutcome(validated_plan=validated, reflection=None, errors=[])

        await self._log_event(
            "plan.invalid",
            {
                "milestone_id": milestone.milestone_id,
                "run_id": ctx.run_id,
                "errors": validation.errors,
            },
        )
        reflection = await self._remediator.remediate(
            VerifyResult(success=False, errors=validation.errors, evidence=[]),
            milestone_ctx.tool_errors,
            milestone_ctx,
            ctx,
        )
        return PlanLoopOutcome(validated_plan=None, reflection=reflection, errors=validation.errors)

    def _build_validated_plan(self, proposed_plan: ProposedPlan) -> ValidatedPlan:
        validated_steps: list[ValidatedStep] = []
        for step in proposed_plan.proposed_steps:
            tool = self._tool_runtime.get_tool(step.tool_name)
            step_type = StepType.WORKUNIT if tool and tool.is_work_unit else StepType.ATOMIC
            risk_level = tool.risk_level if tool else RiskLevel.READ_ONLY
            validated_steps.append(
                ValidatedStep(
                    step_id=step.step_id,
                    step_type=step_type,
                    tool_name=step.tool_name,
                    risk_level=risk_level,
                    tool_input=step.tool_input,
                    description=step.description,
                    envelope=step.envelope,
                    done_predicate=step.done_predicate,
                )
            )
        return ValidatedPlan(
            plan_description=proposed_plan.plan_description,
            steps=validated_steps,
            metadata=proposed_plan.metadata,
        )

    async def _execute_loop(
        self,
        plan: ValidatedPlan,
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> ExecuteResult:
        outputs: list = []
        errors: list[str] = []
        for step in plan.steps:
            if self._tool_runtime.is_plan_tool(step.tool_name):
                await self._log_event(
                    "plan.tool_encountered",
                    {"tool": step.tool_name, "run_id": ctx.run_id, "step_id": step.step_id},
                )
                return ExecuteResult(
                    success=False,
                    outputs=outputs,
                    errors=errors,
                    encountered_plan_tool=True,
                    plan_tool_name=step.tool_name,
                )
            try:
                await self._log_event(
                    "tool.invoke",
                    {"tool": step.tool_name, "run_id": ctx.run_id, "step_id": step.step_id},
                )
                result = await self._tool_runtime.invoke(
                    step.tool_name,
                    step.tool_input,
                    ctx,
                    envelope=step.envelope,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                milestone_ctx.add_error(
                    ToolErrorRecord(
                        error_type="tool_exception",
                        tool_name=step.tool_name,
                        message=str(exc),
                    )
                )
                await self._log_event(
                    "tool.error",
                    {"tool": step.tool_name, "error": str(exc), "run_id": ctx.run_id},
                )
                return ExecuteResult(success=False, outputs=outputs, errors=errors)
            outputs.append(result)
            milestone_ctx.evidence_collected.extend(result.evidence)
            if not result.success:
                errors.append(result.error or "tool failed")
                milestone_ctx.add_error(
                    ToolErrorRecord(
                        error_type="tool_failure",
                        tool_name=step.tool_name,
                        message=result.error or "tool failed",
                    )
                )
        return ExecuteResult(success=not errors, outputs=outputs, errors=errors)

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        await self._event_log.append(Event(event_type=event_type, payload=payload))
