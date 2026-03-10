"""Session-loop orchestration helpers for DareAgent.

This module isolates Layer-1 session lifecycle control flow from the DareAgent
facade.
"""

from __future__ import annotations

import json
import time
from typing import Any, Protocol
from uuid import uuid4

from dare_framework.context import Message
from dare_framework.context.types import MessageKind, MessageRole
from dare_framework.agent._internal.orchestration import MilestoneState, SessionState
from dare_framework.plan.types import MilestoneSummary, RunResult, SessionSummary, Task


def _to_json_safe(value: Any, *, _seen: set[int] | None = None) -> Any:
    """Best-effort conversion for values that must survive JSON event persistence."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if _seen is None:
        _seen = set()
    if isinstance(value, (dict, list, tuple, set)):
        marker = id(value)
        if marker in _seen:
            return "<circular>"
        _seen.add(marker)
    if isinstance(value, dict):
        try:
            return {str(key): _to_json_safe(item, _seen=_seen) for key, item in value.items()}
        finally:
            _seen.remove(marker)
    if isinstance(value, set):
        try:
            normalized = [_to_json_safe(item, _seen=_seen) for item in value]
            # Sort by canonical JSON representation so mixed nested values remain deterministic.
            return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
        finally:
            _seen.remove(marker)
    if isinstance(value, (list, tuple)):
        try:
            return [_to_json_safe(item, _seen=_seen) for item in value]
        finally:
            _seen.remove(marker)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    # Fall back to stable string form for custom objects (Path/datetime/etc.).
    return str(value)


class SessionOrchestratorAgent(Protocol):
    """Minimal DareAgent contract required by session-loop orchestration."""

    _context: Any
    _session_state: SessionState | None
    _planner: Any
    _exec_ctl: Any

    async def _emit_hook(self, phase: Any, payload: dict[str, Any]) -> Any: ...

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None: ...

    async def _run_milestone_loop(self, milestone: Any, *, transport: Any | None = None) -> Any: ...

    def _poll_or_raise(self) -> None: ...

    def _log(self, message: str) -> None: ...

    def _budget_stats(self) -> dict[str, Any]: ...


async def run_session_loop(
    agent: SessionOrchestratorAgent,
    task: Task,
    *,
    transport: Any | None = None,
) -> RunResult:
    """Run the Layer-1 session loop."""
    if agent._session_state is None:
        agent._session_state = SessionState(
            task_id=task.task_id or uuid4().hex[:8],
        )
    session_start_monotonic = time.perf_counter()
    session_started_at = time.time()
    from dare_framework.hook.types import HookPhase

    await agent._emit_hook(HookPhase.BEFORE_SESSION, {
        "task_id": agent._session_state.task_id,
        "run_id": agent._session_state.run_id,
    })

    await agent._log_event("session.start", {
        "task_id": agent._session_state.task_id,
        "run_id": agent._session_state.run_id,
    })

    user_message = task.input_message or Message(
        role=MessageRole.USER,
        kind=MessageKind.CHAT,
        text=task.description,
        metadata=dict(task.metadata),
    )
    agent._context.stm_add(user_message)

    if task.milestones:
        milestones = list(task.milestones)
        await agent._log_event("session.milestones_predefined", {
            "count": len(milestones),
        })
    elif agent._planner is not None:
        agent._log("Decomposing task into milestones...")
        decomposition = await agent._planner.decompose(task, agent._context)
        milestones = decomposition.milestones
        await agent._log_event("session.milestones_decomposed", {
            "count": len(milestones),
            "reasoning": decomposition.reasoning,
        })
    else:
        milestones = task.to_milestones()
        await agent._log_event("session.milestones_default", {
            "count": len(milestones),
        })

    for milestone in milestones:
        agent._session_state.milestone_states.append(
            MilestoneState(milestone=milestone)
        )

    milestone_results = []
    errors: list[str] = []

    for idx, milestone in enumerate(milestones):
        agent._session_state.current_milestone_idx = idx
        agent._log(f"Starting milestone {idx + 1}/{len(milestones)}: {milestone.milestone_id}")

        agent._context.budget_check()

        if agent._exec_ctl is not None:
            agent._poll_or_raise()

        result = await agent._run_milestone_loop(milestone, transport=transport)
        milestone_results.append(result)
        agent._log(f"Milestone {idx + 1} result: success={result.success}")

        if not result.success:
            errors.extend(result.errors or ["milestone failed"])
            break

    success = not errors
    await agent._log_event("session.complete", {
        "task_id": agent._session_state.task_id,
        "run_id": agent._session_state.run_id,
        "success": success,
    })
    await agent._emit_hook(HookPhase.AFTER_SESSION, {
        "success": success,
        "duration_ms": (time.perf_counter() - session_start_monotonic) * 1000.0,
        "budget_stats": agent._budget_stats(),
    })

    output = None
    if milestone_results:
        last_result = milestone_results[-1]
        if last_result.outputs:
            output = last_result.outputs[-1]
    summary_output = _to_json_safe(output)

    milestone_summaries: list[MilestoneSummary] = []
    for idx, result in enumerate(milestone_results):
        state = agent._session_state.milestone_states[idx]
        milestone_summaries.append(
            MilestoneSummary(
                milestone_id=state.milestone.milestone_id,
                description=state.milestone.description,
                attempts=state.attempts,
                success=result.success,
                outputs=[_to_json_safe(item) for item in result.outputs],
                errors=list(result.errors),
                evidence_count=len(state.evidence_collected),
                reflections_count=len(state.reflections),
            )
        )

    session_ended_at = time.time()
    session_summary = SessionSummary(
        session_id=agent._session_state.run_id,
        task_id=agent._session_state.task_id,
        success=success,
        started_at=session_started_at,
        ended_at=session_ended_at,
        duration_ms=(time.perf_counter() - session_start_monotonic) * 1000.0,
        milestones=milestone_summaries,
        final_output=summary_output,
        errors=list(errors),
        metadata={"milestone_count": len(milestones)},
    )
    await agent._log_event("session.summary", {"summary": session_summary.to_dict()})

    return RunResult(
        success=success,
        output=output,
        errors=errors,
        session_id=agent._session_state.run_id,
        session_summary=session_summary,
    )


__all__ = ["run_session_loop"]
