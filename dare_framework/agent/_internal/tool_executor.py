"""Tool loop execution helpers for DareAgent.

This module isolates the Layer-5 tool-loop control flow from the DareAgent
facade while preserving runtime behavior.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from dare_framework.hook.types import HookDecision, HookPhase
from dare_framework.plan.types import DonePredicate, ToolLoopRequest
from dare_framework.tool._internal.governed_tool_gateway import ApprovalInvokeContext


class ToolExecutorAgent(Protocol):
    """Minimal DareAgent contract required by tool-loop execution."""

    _context: Any
    _session_state: Any
    _max_tool_iterations: int
    _governed_tool_gateway: Any

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> Any: ...

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None: ...

    def _budget_stats(self) -> dict[str, Any]: ...

    def _risk_level_value(self, descriptor: Any | None) -> int: ...

    def _requires_approval(self, descriptor: Any | None) -> bool: ...

    def _tool_loop_max_calls(self, envelope: Any) -> int | None: ...


async def run_tool_loop(
    agent: ToolExecutorAgent,
    request: ToolLoopRequest,
    *,
    transport: Any | None,
    tool_name: str,
    tool_call_id: str,
    descriptor: Any | None = None,
) -> dict[str, Any]:
    """Run the tool loop for a single tool invocation request."""
    agent._context.budget_check()

    done_predicate = request.envelope.done_predicate
    max_calls = agent._tool_loop_max_calls(request.envelope)
    attempts = 0
    risk_level = agent._risk_level_value(descriptor)
    requires_approval = agent._requires_approval(descriptor)
    session_id = agent._session_state.run_id if agent._session_state is not None else None

    while True:
        attempts += 1
        agent._context.budget_check()
        agent._context.budget_use("tool_calls", 1)

        tool_start = time.perf_counter()
        before_tool_dispatch = await agent._emit_hook(
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
        if before_tool_dispatch.decision in {HookDecision.BLOCK, HookDecision.ASK}:
            policy_error = (
                "tool invocation requires hook approval"
                if before_tool_dispatch.decision is HookDecision.ASK
                else "tool invocation denied by hook policy"
            )
            await agent._emit_hook(
                HookPhase.AFTER_TOOL,
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "capability_id": request.capability_id,
                    "attempt": attempts,
                    "success": False,
                    "error": policy_error,
                    "approved": True,
                    "evidence_collected": False,
                    "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                    "budget_stats": agent._budget_stats(),
                },
            )
            return {
                "success": False,
                "error": policy_error,
                "output": {},
            }
        await agent._log_event("tool.invoke", {
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "capability_id": request.capability_id,
            "attempt": attempts,
        })

        try:
            approval_ctx = ApprovalInvokeContext(
                session_id=session_id,
                transport=transport,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                event_logger=agent._log_event,
                runtime_context=agent._context,
            )
            result = await agent._governed_tool_gateway.invoke(
                request.capability_id,
                approval_ctx,
                envelope=request.envelope,
                **request.params,
            )

            await agent._log_event("tool.result", {
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
            denied_status = "fail"
            denied_output = getattr(result, "output", {})
            approved = True
            if not tool_success:
                if isinstance(denied_output, dict):
                    candidate_status = denied_output.get("status")
                    if isinstance(candidate_status, str) and candidate_status:
                        denied_status = candidate_status
                approved = denied_status != "not_allow"
            await agent._emit_hook(
                HookPhase.AFTER_TOOL,
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "capability_id": request.capability_id,
                    "attempt": attempts,
                    "success": tool_success,
                    "error": result.error if hasattr(result, "error") else None,
                    "approved": approved,
                    "evidence_collected": evidence_collected,
                    "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                    "budget_stats": agent._budget_stats(),
                },
            )

            if not tool_success:
                return {
                    "success": False,
                    "status": denied_status,
                    "error": result.error or "tool failed",
                    "output": denied_output,
                    "result": result,
                }

            milestone_state = agent._session_state.current_milestone_state
            if milestone_state and hasattr(result, "evidence"):
                for evidence in result.evidence:
                    milestone_state.add_evidence(evidence)

            if done_predicate is None or _done_predicate_satisfied(done_predicate, result):
                return {
                    "success": True,
                    "status": "success",
                    "output": getattr(result, "output", {}),
                    "error": getattr(result, "error", None),
                    "result": result,
                }

            if max_calls is not None and attempts >= max_calls:
                return {
                    "success": False,
                    "status": "fail",
                    "error": "done predicate not satisfied before budget exhausted",
                    "output": getattr(result, "output", {}),
                    "result": result,
                }

        except Exception as e:
            await agent._log_event("tool.error", {
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
            await agent._emit_hook(
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
                    "budget_stats": agent._budget_stats(),
                },
            )
            return {
                "success": False,
                "status": "fail",
                "error": str(e),
                "output": {},
            }


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


__all__ = ["run_tool_loop"]
