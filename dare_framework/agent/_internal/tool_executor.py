"""Tool-loop orchestration helpers for DareAgent.

This module isolates Layer-5 tool-loop control flow from the DareAgent facade.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from dare_framework.hook.types import HookDecision, HookPhase
from dare_framework.plan.types import DonePredicate, ToolLoopRequest
from dare_framework.security import SandboxSpec
from dare_framework.tool._internal.governed_tool_gateway import ApprovalInvokeContext


class ToolExecutorAgent(Protocol):
    """Minimal DareAgent contract required by tool-loop execution."""

    _context: Any
    _governed_tool_gateway: Any
    _security_boundary: Any
    _session_state: Any

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> Any: ...

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None: ...

    async def _resolve_tool_approval(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        tool_name: str,
        tool_call_id: str,
        transport: Any | None,
    ) -> tuple[bool, str | None]: ...

    async def _resolve_tool_security(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        tool_name: str,
        risk_level: int,
        requires_approval: bool,
    ) -> tuple[dict[str, Any], str | None]: ...

    def _budget_stats(self) -> dict[str, Any]: ...

    def _requires_approval(self, descriptor: Any | None) -> bool: ...

    def _risk_level_value(self, descriptor: Any | None) -> int: ...

    def _risk_level_value_from_envelope(self, envelope: Any) -> int: ...

    def _tool_loop_max_calls(self, envelope: Any) -> int | None: ...


async def run_tool_loop(
    agent: ToolExecutorAgent,
    request: ToolLoopRequest,
    *,
    transport: Any | None,
    tool_name: str,
    tool_call_id: str,
    descriptor: Any | None = None,
    requires_approval_override: bool | None = None,
) -> dict[str, Any]:
    """Run the tool loop for a single tool invocation request."""
    agent._context.budget_check()

    done_predicate = request.envelope.done_predicate
    max_calls = agent._tool_loop_max_calls(request.envelope)
    attempts = 0
    # Use the strictest risk level from descriptor metadata and envelope
    # constraints to avoid silently downgrading policy checks.
    risk_level = max(
        agent._risk_level_value(descriptor),
        agent._risk_level_value_from_envelope(request.envelope),
    )
    descriptor_requires_approval = agent._requires_approval(descriptor)
    metadata_requires_approval = requires_approval_override is True
    requires_approval = descriptor_requires_approval
    session_id = agent._session_state.run_id if agent._session_state is not None else None

    while True:
        attempts += 1
        agent._context.budget_check()
        agent._context.budget_use("tool_calls", 1)
        tool_start = time.perf_counter()
        try:
            trusted_params, trust_error = await agent._resolve_tool_security(
                capability_id=request.capability_id,
                params=request.params,
                tool_name=tool_name,
                risk_level=risk_level,
                requires_approval=descriptor_requires_approval or metadata_requires_approval,
            )
        except Exception as e:
            await agent._log_event(
                "tool.error",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "error": str(e),
                    "attempt": attempts,
                },
            )
            await agent._emit_hook(
                HookPhase.AFTER_TOOL,
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "capability_id": request.capability_id,
                    "attempt": attempts,
                    "success": False,
                    "error": str(e),
                    "approved": False,
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

        approval_required_by_policy = trust_error == "tool invocation requires security approval"
        requires_approval = (
            descriptor_requires_approval
            or metadata_requires_approval
            or approval_required_by_policy
        )
        if trust_error is not None:
            if approval_required_by_policy:
                trust_error = None
            if trust_error is not None:
                await agent._log_event(
                    "security.tool.policy",
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "capability_id": request.capability_id,
                        "error": trust_error,
                        "attempt": attempts,
                    },
                )
                await agent._emit_hook(
                    HookPhase.AFTER_TOOL,
                    {
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "capability_id": request.capability_id,
                        "attempt": attempts,
                        "success": False,
                        "error": trust_error,
                        "approved": False,
                        "evidence_collected": False,
                        "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                        "budget_stats": agent._budget_stats(),
                    },
                )
                return {
                    "success": False,
                    "status": "not_allow",
                    "error": trust_error,
                    "output": {},
                }

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

        # Descriptor-gated approvals are enforced by governed gateway invoke;
        # policy-only / metadata approvals need explicit checks per attempt.
        if requires_approval and not descriptor_requires_approval:
            approved, approval_error = await agent._resolve_tool_approval(
                capability_id=request.capability_id,
                params=trusted_params,
                session_id=session_id,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                transport=transport,
            )
            if not approved:
                approval_error_text = approval_error or "tool invocation requires security approval"
                status = "not_allow" if "denied" in approval_error_text.lower() else "fail"
                await agent._log_event(
                    "security.tool.policy",
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "capability_id": request.capability_id,
                        "error": approval_error_text,
                        "attempt": attempts,
                    },
                )
                await agent._emit_hook(
                    HookPhase.AFTER_TOOL,
                    {
                        "tool_call_id": tool_call_id,
                        "tool_name": tool_name,
                        "capability_id": request.capability_id,
                        "attempt": attempts,
                        "success": False,
                        "error": approval_error_text,
                        "approved": False,
                        "evidence_collected": False,
                        "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                        "budget_stats": agent._budget_stats(),
                    },
                )
                return {
                    "success": False,
                    "error": approval_error_text,
                    "status": status,
                    "output": {},
                }

        await agent._log_event(
            "tool.invoke",
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "capability_id": request.capability_id,
                "attempt": attempts,
            },
        )

        try:
            approval_ctx = ApprovalInvokeContext(
                session_id=session_id,
                transport=transport,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                event_logger=agent._log_event,
                runtime_context=agent._context,
            )
            result = await agent._security_boundary.execute_safe(
                action="invoke_tool",
                fn=lambda: agent._governed_tool_gateway.invoke(
                    request.capability_id,
                    approval_ctx,
                    envelope=request.envelope,
                    **trusted_params,
                ),
                sandbox=SandboxSpec(
                    mode="tool_gateway",
                    details={
                        "capability_id": request.capability_id,
                        "tool_name": tool_name,
                    },
                ),
            )

            await agent._log_event(
                "tool.result",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "success": getattr(result, "success", True),
                    "attempt": attempts,
                },
            )

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

            milestone_state = (
                agent._session_state.current_milestone_state
                if agent._session_state is not None
                else None
            )
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
            await agent._log_event(
                "tool.error",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "error": str(e),
                    "attempt": attempts,
                },
            )
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
