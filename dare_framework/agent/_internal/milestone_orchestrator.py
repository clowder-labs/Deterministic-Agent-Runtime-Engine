"""Milestone-loop orchestration helpers for DareAgent.

This module isolates Layer-2 milestone control flow from the DareAgent facade.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from dare_framework.agent._internal.orchestration import MilestoneResult
from dare_framework.hook.types import HookPhase
from dare_framework.plan.types import Milestone, VerifyResult


class MilestoneOrchestratorAgent(Protocol):
    """Minimal DareAgent contract required by milestone-loop orchestration."""

    _context: Any
    _session_state: Any
    _max_milestone_attempts: int
    _sandbox: Any
    _remediator: Any

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> Any: ...

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None: ...

    async def _run_plan_loop(self, milestone: Milestone) -> Any: ...

    async def _run_execute_loop(self, plan: Any, *, transport: Any | None = None) -> dict[str, Any]: ...

    async def _verify_milestone(self, execute_result: dict[str, Any], validated_plan: Any | None = None) -> Any: ...

    async def _check_plan_policy(self, milestone: Milestone, validated_plan: Any | None) -> tuple[str | None, str]: ...

    def _budget_stats(self) -> dict[str, Any]: ...

    def _log(self, message: str) -> None: ...


async def run_milestone_loop(
    agent: MilestoneOrchestratorAgent,
    milestone: Milestone,
    *,
    transport: Any | None = None,
) -> MilestoneResult:
    """Run the Layer-2 milestone loop."""
    milestone_start = time.perf_counter()
    await agent._emit_hook(HookPhase.BEFORE_MILESTONE, {
        "milestone_id": milestone.milestone_id,
        "milestone_index": agent._session_state.current_milestone_idx if agent._session_state else None,
    })
    await agent._log_event("milestone.start", {
        "milestone_id": milestone.milestone_id,
    })

    milestone_state = agent._session_state.current_milestone_state

    for attempt in range(agent._max_milestone_attempts):
        if milestone_state is not None:
            milestone_state.attempts = attempt + 1
        agent._log(f"Milestone attempt {attempt + 1}/{agent._max_milestone_attempts}")
        agent._context.budget_check()

        snapshot_id = None
        if agent._sandbox is not None:
            snapshot_id = agent._sandbox.create_snapshot(agent._context)
            agent._log(f"Created STM snapshot: {snapshot_id}")

        agent._log("Running plan loop...")
        validated_plan = await agent._run_plan_loop(milestone)
        agent._log(f"Plan loop done, validated_plan={validated_plan is not None}")

        plan_policy_error: str | None = None
        plan_policy_decision = "not_applicable"
        if validated_plan is not None:
            try:
                plan_policy_error, plan_policy_decision = await agent._check_plan_policy(
                    milestone,
                    validated_plan,
                )
            except Exception as exc:
                # Keep the failure scoped to the milestone and avoid failing the
                # whole run when policy backends are temporarily unavailable.
                plan_policy_error = f"plan policy evaluation failed: {exc}"
                plan_policy_decision = "error"
        if plan_policy_error is not None:
            if agent._sandbox is not None and snapshot_id:
                agent._sandbox.rollback(agent._context, snapshot_id)
                agent._log(f"Rolled back STM snapshot: {snapshot_id}")
            await agent._log_event(
                "security.plan.policy",
                {
                    "milestone_id": milestone.milestone_id,
                    "decision": plan_policy_decision,
                    "error": plan_policy_error,
                },
            )
            await agent._log_event(
                "milestone.failed",
                {
                    "milestone_id": milestone.milestone_id,
                    "attempts": attempt + 1,
                    "reason": "plan_policy",
                },
            )
            await agent._emit_hook(
                HookPhase.AFTER_MILESTONE,
                {
                    "milestone_id": milestone.milestone_id,
                    "success": False,
                    "attempts": attempt + 1,
                    "errors": [plan_policy_error],
                    "duration_ms": (time.perf_counter() - milestone_start) * 1000.0,
                    "budget_stats": agent._budget_stats(),
                },
            )
            return MilestoneResult(
                success=False,
                outputs=[],
                errors=[plan_policy_error],
                verify_result=VerifyResult(success=False, errors=[plan_policy_error]),
            )

        agent._log("Running execute loop...")
        execute_result = await agent._run_execute_loop(validated_plan, transport=transport)
        agent._log(f"Execute loop done, result keys={list(execute_result.keys())}")

        if execute_result.get("encountered_plan_tool", False):
            if milestone_state:
                milestone_state.add_reflection(
                    f"plan tool encountered: {execute_result.get('plan_tool_name')}"
                )
            if agent._sandbox is not None and snapshot_id:
                agent._sandbox.rollback(agent._context, snapshot_id)
                agent._log(f"Rolled back STM snapshot: {snapshot_id}")
            continue

        verify_result = await agent._verify_milestone(execute_result, validated_plan)

        if verify_result.success:
            if agent._sandbox is not None and snapshot_id:
                agent._sandbox.commit(snapshot_id)
                agent._log(f"Committed STM snapshot: {snapshot_id}")

            await agent._log_event("milestone.success", {
                "milestone_id": milestone.milestone_id,
                "attempts": attempt + 1,
            })
            await agent._emit_hook(HookPhase.AFTER_MILESTONE, {
                "milestone_id": milestone.milestone_id,
                "success": True,
                "attempts": attempt + 1,
                "duration_ms": (time.perf_counter() - milestone_start) * 1000.0,
                "budget_stats": agent._budget_stats(),
            })
            return MilestoneResult(
                success=True,
                outputs=execute_result.get("outputs", []),
                errors=[],
                verify_result=verify_result,
            )

        if agent._sandbox is not None and snapshot_id:
            agent._sandbox.rollback(agent._context, snapshot_id)
            agent._log(f"Rolled back STM snapshot: {snapshot_id}")

        if agent._remediator is not None and milestone_state:
            reflection = await agent._remediator.remediate(
                verify_result,
                ctx=agent._context,
            )
            milestone_state.add_reflection(reflection)

    await agent._log_event("milestone.failed", {
        "milestone_id": milestone.milestone_id,
    })
    await agent._emit_hook(HookPhase.AFTER_MILESTONE, {
        "milestone_id": milestone.milestone_id,
        "success": False,
        "attempts": agent._max_milestone_attempts,
        "duration_ms": (time.perf_counter() - milestone_start) * 1000.0,
        "budget_stats": agent._budget_stats(),
    })
    return MilestoneResult(
        success=False,
        outputs=[],
        errors=["milestone failed after max attempts"],
        verify_result=None,
    )


__all__ = ["run_milestone_loop"]
