from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Generic, Iterable, Protocol, TypeVar

from dare_framework.components.interfaces import (
    IContextAssembler,
    IEventLog,
    IHook,
    IModelAdapter,
    IPlanGenerator,
    IPolicyEngine,
    IRemediator,
    ICheckpoint,
    IToolRuntime,
    IValidator,
)
from dare_framework.core.errors import PlanGenerationFailedError, StateError, ToolExecutionError, UserInterruptedError
from dare_framework.core.events import PlanValidationFailedEvent, RemediateEvent, SessionStartedEvent
from dare_framework.core.models import (
    Budget,
    DonePredicate,
    Envelope,
    EnvelopeBudget,
    ExecuteResult,
    QualityMetrics,
    Message,
    Milestone,
    MilestoneContext,
    MilestoneResult,
    MilestoneSummary,
    RunContext,
    RunResult,
    SessionContext,
    SessionResult,
    SessionSummary,
    Task,
    ToolError,
    ToolResult,
    ValidatedPlan,
    VerifyResult,
)
from dare_framework.core.state import RuntimeState

DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")


class IRuntime(Protocol, Generic[DepsT, OutputT]):
    async def init(self, task: Task) -> None:
        ...

    async def run(self, task: Task, deps: DepsT) -> RunResult[OutputT]:
        ...

    async def pause(self) -> None:
        ...

    async def resume(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    async def cancel(self) -> None:
        ...

    def get_state(self) -> RuntimeState:
        ...


@dataclass
class ToolLoopContext:
    tool_name: str
    tool_input: dict
    evidence: list[object]

    def add_evidence(self, evidence_ref: object) -> None:
        self.evidence.append(evidence_ref)


class AgentRuntime(Generic[DepsT, OutputT], IRuntime[DepsT, OutputT]):
    def __init__(
        self,
        *,
        event_log: IEventLog,
        tool_runtime: IToolRuntime,
        policy_engine: IPolicyEngine,
        plan_generator: IPlanGenerator,
        validator: IValidator,
        remediator: IRemediator,
        context_assembler: IContextAssembler,
        model_adapter: IModelAdapter,
        checkpoint: ICheckpoint,
        hooks: Iterable[IHook] | None = None,
    ) -> None:
        self.event_log = event_log
        self.tool_runtime = tool_runtime
        self.policy_engine = policy_engine
        self.plan_generator = plan_generator
        self.validator = validator
        self.remediator = remediator
        self.context_assembler = context_assembler
        self.model_adapter = model_adapter
        self.checkpoint = checkpoint
        self.hooks = list(hooks or [])

        self._state = RuntimeState.READY
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        self._pending_plan: ValidatedPlan | None = None
        self._current_milestone_id: str | None = None
        self._previous_session_summary: SessionSummary | None = None
        self._task_id: str | None = None

    async def init(self, task: Task) -> None:
        self._state = RuntimeState.READY
        await self._notify_hooks_session_start(task)

    async def run(self, task: Task, deps: DepsT) -> RunResult[OutputT]:
        if self._state != RuntimeState.READY:
            raise StateError(f"Invalid state for run: {self._state}")

        self._task_id = task.task_id
        self._state = RuntimeState.RUNNING
        ctx = RunContext(deps=deps, run_id=f"run_{task.task_id}")

        previous_summary = self._previous_session_summary
        if isinstance(task.context.get("previous_session_summary"), SessionSummary):
            previous_summary = task.context.get("previous_session_summary")

        try:
            session_result = await self._session_loop(
                user_input=task.description,
                previous_session_summary=previous_summary,
                ctx=ctx,
            )
            run_result = RunResult(
                success=True,
                output=None,
                session_summary=session_result.session_summary,
            )
            await self._notify_hooks_session_end(run_result)
            return run_result
        finally:
            if self._state == RuntimeState.RUNNING:
                await self.stop()

    async def pause(self) -> None:
        if self._state != RuntimeState.RUNNING:
            raise StateError(f"Invalid state for pause: {self._state}")
        self._state = RuntimeState.PAUSED
        self._resume_event.clear()
        await self.checkpoint.save(
            task_id=self._task_id or "runtime",
            state=self._state,
            milestone_id=self._current_milestone_id,
        )

    async def resume(self) -> None:
        if self._state != RuntimeState.PAUSED:
            raise StateError(f"Invalid state for resume: {self._state}")
        self._state = RuntimeState.RUNNING
        self._resume_event.set()

    async def stop(self) -> None:
        if self._state not in {RuntimeState.RUNNING, RuntimeState.PAUSED}:
            raise StateError(f"Invalid state for stop: {self._state}")
        self._state = RuntimeState.STOPPED
        self._resume_event.set()
        await self.checkpoint.save(
            task_id=self._task_id or "runtime",
            state=self._state,
            milestone_id=self._current_milestone_id,
        )

    async def cancel(self) -> None:
        self._state = RuntimeState.CANCELLED
        self._resume_event.set()
        await self.checkpoint.save(
            task_id=self._task_id or "runtime",
            state=self._state,
            milestone_id=self._current_milestone_id,
        )

    def get_state(self) -> RuntimeState:
        return self._state

    def get_pending_plan(self) -> ValidatedPlan | None:
        return self._pending_plan

    async def _session_loop(
        self,
        user_input: str,
        previous_session_summary: SessionSummary | None,
        ctx: RunContext[DepsT],
    ) -> SessionResult:
        session_ctx = SessionContext(
            user_input=user_input,
            previous_session_summary=previous_session_summary,
            milestone_summaries=[],
            start_time=time.time(),
        )

        await self.event_log.append(
            SessionStartedEvent(
                user_input=user_input,
                has_previous_context=previous_session_summary is not None,
            )
        )

        milestones = await self._plan_milestones(user_input, previous_session_summary, ctx)

        for index, milestone in enumerate(milestones):
            if self._state in {RuntimeState.STOPPED, RuntimeState.CANCELLED}:
                break

            self._current_milestone_id = milestone.milestone_id
            await self._notify_hooks_milestone_start(milestone)

            if await self.checkpoint.is_completed(milestone.milestone_id):
                summary = await self.checkpoint.load_milestone_summary(milestone.milestone_id)
                session_ctx.milestone_summaries.append(summary)
                continue

            milestone_result = await self._milestone_loop(
                milestone=milestone,
                previous_milestone_summaries=session_ctx.milestone_summaries,
                ctx=ctx,
            )

            summary = await self._summarize_milestone(
                milestone=milestone,
                result=milestone_result,
                milestone_index=index,
                total_milestones=len(milestones),
                ctx=ctx,
            )

            session_ctx.milestone_summaries.append(summary)
            await self._persist_milestone_summary(milestone.milestone_id, summary)

        session_summary = await self._summarize_session(session_ctx, ctx)
        await self.checkpoint.save_session_summary(session_summary)

        return SessionResult(session_summary=session_summary)

    async def _milestone_loop(
        self,
        milestone: Milestone,
        previous_milestone_summaries: list[MilestoneSummary],
        ctx: RunContext[DepsT],
    ) -> MilestoneResult:
        milestone_ctx = MilestoneContext(
            user_input=milestone.user_input,
            milestone_description=milestone.description,
        )

        milestone_budget = Budget(max_attempts=10, max_time_seconds=600, max_tool_calls=100)
        execute_result: ExecuteResult | None = None
        verify_result: VerifyResult | None = None

        while not milestone_budget.exceeded():
            milestone_budget.record_attempt()

            await self.context_assembler.assemble(
                milestone=milestone,
                milestone_ctx=milestone_ctx,
                ctx=ctx,
            )

            try:
                validated_plan = await self._plan_loop(milestone, milestone_ctx, ctx)
            except PlanGenerationFailedError as exc:
                return MilestoneResult(
                    milestone_id=milestone.milestone_id,
                    deliverables=[],
                    evidence=[],
                    quality_metrics=QualityMetrics(),
                    completeness=0.0,
                    last_verify_result=None,
                    attempts=milestone_budget.current_attempts,
                    tool_calls=milestone_budget.current_tool_calls,
                    duration_seconds=time.time() - milestone_budget.start_time,
                    termination_reason="plan_generation_failed",
                    errors=[
                        ToolError(
                            error_type="plan_failure",
                            tool_name="plan_loop",
                            message=str(exc),
                        )
                    ],
                )

            if self.policy_engine.needs_approval(milestone, validated_plan):
                self._pending_plan = validated_plan
                await self.pause()
                await self._wait_for_resume()
                self._pending_plan = None

                if self._state in {RuntimeState.CANCELLED, RuntimeState.STOPPED}:
                    break

            execute_result = await self._execute_loop(
                validated_plan=validated_plan,
                milestone_ctx=milestone_ctx,
                budget=milestone_budget,
                ctx=ctx,
            )

            if execute_result.encountered_plan_tool:
                milestone_ctx.add_reflection(
                    f"Encountered plan tool '{execute_result.plan_tool_name}' during execution."
                    " Re-planning required."
                )
                continue

            verify_result = await self.validator.validate_milestone(milestone, execute_result, ctx)

            if verify_result.passed:
                return MilestoneResult(
                    milestone_id=milestone.milestone_id,
                    deliverables=[e.evidence_id for e in execute_result.evidence],
                    evidence=execute_result.evidence,
                    quality_metrics=verify_result.quality_metrics,
                    completeness=verify_result.completeness,
                    last_verify_result=verify_result,
                    attempts=milestone_budget.current_attempts,
                    tool_calls=milestone_budget.current_tool_calls,
                    duration_seconds=time.time() - milestone_budget.start_time,
                    termination_reason="verify_pass",
                )

            reflection = await self.remediator.remediate(
                verify_result=verify_result,
                tool_errors=milestone_ctx.tool_errors,
                milestone_ctx=milestone_ctx,
                ctx=ctx,
            )
            milestone_ctx.add_reflection(reflection)
            await self.event_log.append(
                RemediateEvent(
                    milestone_id=milestone.milestone_id,
                    attempt=milestone_budget.current_attempts,
                    failure_reason=verify_result.failure_reason,
                    reflection=reflection,
                )
            )

        return MilestoneResult(
            milestone_id=milestone.milestone_id,
            deliverables=[e.evidence_id for e in execute_result.evidence] if execute_result else [],
            evidence=execute_result.evidence if execute_result else [],
            quality_metrics=verify_result.quality_metrics if verify_result else QualityMetrics(),
            completeness=verify_result.completeness if verify_result else 0.0,
            last_verify_result=verify_result,
            attempts=milestone_budget.current_attempts,
            tool_calls=milestone_budget.current_tool_calls,
            duration_seconds=time.time() - milestone_budget.start_time,
            termination_reason="budget_exceeded",
        )

    async def _plan_loop(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        ctx: RunContext[DepsT],
    ) -> ValidatedPlan:
        plan_budget = Budget(max_attempts=5, max_time_seconds=120, max_tool_calls=0)
        plan_attempts: list[dict[str, object]] = []

        while not plan_budget.exceeded():
            plan_budget.record_attempt()

            proposed_plan = await self.plan_generator.generate_plan(
                milestone=milestone,
                milestone_ctx=milestone_ctx,
                plan_attempts=plan_attempts,
                ctx=ctx,
            )

            validation_result = await self.validator.validate_plan(proposed_plan.proposed_steps, ctx)

            if validation_result.is_valid:
                return ValidatedPlan(
                    plan_description=proposed_plan.plan_description,
                    steps=validation_result.validated_steps,
                    metadata={
                        "plan_attempts": plan_budget.current_attempts,
                        "discarded_attempts": len(plan_attempts),
                    },
                )

            plan_attempts.append(
                {
                    "attempt": plan_budget.current_attempts,
                    "proposed_plan": proposed_plan,
                    "validation_errors": validation_result.errors,
                    "timestamp": time.time(),
                }
            )

            await self.event_log.append(
                PlanValidationFailedEvent(
                    milestone_id=milestone.milestone_id,
                    attempt=plan_budget.current_attempts,
                    errors=validation_result.errors,
                )
            )

        raise PlanGenerationFailedError(
            f"Failed to generate valid plan after {plan_budget.current_attempts} attempts."
        )

    async def _execute_loop(
        self,
        validated_plan: ValidatedPlan,
        milestone_ctx: MilestoneContext,
        budget: Budget,
        ctx: RunContext[DepsT],
    ) -> ExecuteResult:
        execute_result = ExecuteResult(
            evidence=[],
            successful_tool_calls=[],
            execution_trace=[],
        )

        execution_messages = [
            Message(
                role="system",
                content=self._build_execution_system_prompt(milestone_ctx),
            ),
            Message(
                role="user",
                content=(
                    "Execute this plan:\n\n"
                    f"{validated_plan.plan_description}\n\n"
                    f"Available tools: {self._format_tool_definitions()}\n\n"
                    "Execute step by step. After each tool call, assess and decide next action."
                ),
            ),
        ]

        max_iterations = 50

        for iteration in range(max_iterations):
            if budget.exceeded():
                execute_result.termination_reason = "budget_exceeded"
                break

            response = await self.model_adapter.generate(
                messages=execution_messages,
                tools=self.tool_runtime.list_tools(),
            )

            if not response.tool_calls:
                execute_result.termination_reason = "llm_declares_done"
                execute_result.llm_conclusion = response.content
                break

            tool_results: list[Message] = []

            for tool_call in response.tool_calls:
                if self.tool_runtime.is_plan_tool(tool_call.name):
                    execute_result.encountered_plan_tool = True
                    execute_result.plan_tool_name = tool_call.name
                    execute_result.termination_reason = "plan_tool_encountered"
                    return execute_result

                try:
                    result = await self.tool_runtime.invoke(
                        name=tool_call.name,
                        input=tool_call.input,
                        ctx=ctx,
                    )
                    budget.record_tool_call()

                    execute_result.successful_tool_calls.append(
                        {
                            "tool": tool_call.name,
                            "input": tool_call.input,
                            "output": result.output,
                        }
                    )

                    if result.evidence_ref:
                        execute_result.evidence.append(result.evidence_ref)

                    tool_results.append(
                        Message(
                            role="tool",
                            content=str(result.output),
                        )
                    )

                except (UserInterruptedError, ToolExecutionError) as exc:
                    error = ToolError(
                        error_type="user_interrupted"
                        if isinstance(exc, UserInterruptedError)
                        else "tool_failure",
                        tool_name=tool_call.name,
                        message=str(exc),
                        user_hint=getattr(exc, "user_message", None),
                    )
                    milestone_ctx.add_error(error)

                    tool_results.append(
                        Message(
                            role="tool",
                            content=f"ERROR: {str(exc)}",
                        )
                    )

            execution_messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )
            execution_messages.extend(tool_results)

        if iteration >= max_iterations - 1:
            execute_result.termination_reason = "max_iterations_reached"

        return execute_result

    async def _tool_loop(
        self,
        tool_name: str,
        tool_input: dict,
        envelope: Envelope,
        done_predicate: DonePredicate,
        ctx: RunContext,
    ) -> ToolResult:
        tool_loop_ctx = ToolLoopContext(
            tool_name=tool_name,
            tool_input=tool_input,
            evidence=[],
        )

        tool_budget: EnvelopeBudget = envelope.budget
        while not tool_budget.exceeded():
            tool_budget.record_attempt()
            action_result = await self.tool_runtime.invoke(tool_name, tool_input, ctx)
            tool_budget.record_tool_call()

            if action_result.evidence_ref:
                tool_loop_ctx.add_evidence(action_result.evidence_ref)

            if done_predicate.is_satisfied(tool_loop_ctx.evidence):
                return ToolResult(success=True, output=action_result.output, evidence_ref=action_result.evidence_ref)

        raise ToolExecutionError(
            f"Tool Loop for {tool_name} failed: DonePredicate not satisfied after"
            f" {tool_budget.current_attempts} attempts"
        )

    async def _plan_milestones(
        self,
        user_input: str,
        previous_session_summary: SessionSummary | None,
        ctx: RunContext[DepsT],
    ) -> list[Milestone]:
        return [
            Milestone(
                milestone_id=f"milestone_{ctx.run_id}",
                description=user_input,
                user_input=user_input,
                order=0,
            )
        ]

    async def _summarize_milestone(
        self,
        milestone: Milestone,
        result: MilestoneResult,
        milestone_index: int,
        total_milestones: int,
        ctx: RunContext[DepsT],
    ) -> MilestoneSummary:
        deliverables = result.deliverables
        what_worked = "Delivered outputs." if deliverables else "No deliverables produced."
        what_failed = (
            result.last_verify_result.failure_reason
            if result.last_verify_result and result.last_verify_result.failure_reason
            else "No critical failures reported."
        )
        key_insight = f"Milestone {milestone_index + 1} of {total_milestones} completed."

        return MilestoneSummary(
            milestone_id=milestone.milestone_id,
            milestone_description=milestone.description,
            deliverables=deliverables,
            what_worked=what_worked,
            what_failed=what_failed,
            key_insight=key_insight,
            completeness=result.completeness,
            termination_reason=result.termination_reason,
            attempts=result.attempts,
            duration_seconds=result.duration_seconds,
        )

    async def _summarize_session(
        self,
        session_ctx: SessionContext,
        ctx: RunContext[DepsT],
    ) -> SessionSummary:
        total_attempts = sum(summary.attempts for summary in session_ctx.milestone_summaries)
        key_deliverables: list[str] = []
        for summary in session_ctx.milestone_summaries:
            key_deliverables.extend(summary.deliverables)

        return SessionSummary(
            session_id=ctx.run_id,
            user_input=session_ctx.user_input,
            what_was_accomplished="Completed session milestones.",
            key_deliverables=key_deliverables,
            important_decisions=[],
            lessons_learned=[summary.key_insight for summary in session_ctx.milestone_summaries],
            pending_tasks=[],
            milestone_count=len(session_ctx.milestone_summaries),
            total_attempts=total_attempts,
            duration_seconds=time.time() - session_ctx.start_time,
        )

    def _build_execution_system_prompt(self, milestone_ctx: MilestoneContext) -> str:
        reflections = "\n".join(milestone_ctx.reflections)
        return (
            "You are executing a validated plan.\n"
            f"Milestone: {milestone_ctx.milestone_description}\n"
            f"Reflections:\n{reflections if reflections else 'None'}"
        )

    def _format_tool_definitions(self) -> str:
        tools = self.tool_runtime.list_tools()
        return ", ".join(tool.name for tool in tools)

    async def _wait_for_resume(self) -> None:
        while self._state == RuntimeState.PAUSED:
            await self._resume_event.wait()

    async def _notify_hooks_session_start(self, task: Task) -> None:
        for hook in self.hooks:
            await hook.on_session_start(task)

    async def _notify_hooks_milestone_start(self, milestone: Milestone) -> None:
        for hook in self.hooks:
            await hook.on_milestone_start(milestone)

    async def _notify_hooks_session_end(self, result: RunResult[OutputT]) -> None:
        for hook in self.hooks:
            await hook.on_session_end(result)

    async def _persist_milestone_summary(self, milestone_id: str, summary: MilestoneSummary) -> None:
        await self.checkpoint.save_milestone_summary(milestone_id, summary)
