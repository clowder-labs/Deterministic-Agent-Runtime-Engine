"""Tool-loop orchestration helpers for DareAgent.

This module isolates Layer-5 tool-loop control flow from the DareAgent facade.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from dare_framework.hook.types import HookDecision, HookPhase
from dare_framework.plan.types import DonePredicate, ToolLoopRequest
from dare_framework.security import (
    PolicyDecision,
    SandboxSpec,
    SECURITY_APPROVAL_MANAGER_MISSING,
    SECURITY_POLICY_DENIED,
    SecurityBoundaryError,
)
from dare_framework.tool._internal.governed_tool_gateway import ApprovalInvokeContext


class ToolExecutorAgent(Protocol):
    """Minimal DareAgent contract required by tool-loop execution."""

    _approval_manager: Any
    _context: Any
    _governed_tool_gateway: Any
    _security_boundary: Any
    _session_state: Any

    async def _emit_hook(self, phase: HookPhase, payload: dict[str, Any]) -> Any: ...

    async def _evaluate_tool_security(
        self,
        *,
        request: ToolLoopRequest,
        descriptor: Any | None,
        tool_name: str,
        tool_call_id: str,
        attempt: int,
        requires_approval_override: bool | None = None,
        trusted_risk_level_override: Any | None = None,
    ) -> Any: ...

    async def _log_event(self, event_type: str, payload: dict[str, Any]) -> None: ...

    def _budget_stats(self) -> dict[str, Any]: ...

    def _requires_approval(self, descriptor: Any | None) -> bool: ...

    def _risk_level_from_trusted_input(self, trusted_input: Any) -> int: ...

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
    trusted_risk_level_override: Any | None = None,
) -> dict[str, Any]:
    """Run the tool loop for a single tool invocation request."""
    agent._context.budget_check()

    done_predicate = request.envelope.done_predicate
    max_calls = agent._tool_loop_max_calls(request.envelope)
    attempts = 0
    # Start from the strictest declared risk and let trusted metadata tighten it.
    risk_level = max(
        agent._risk_level_value(descriptor),
        agent._risk_level_value_from_envelope(request.envelope),
    )
    descriptor_requires_approval = agent._requires_approval(descriptor)
    metadata_requires_approval = requires_approval_override is True
    requires_approval = descriptor_requires_approval or metadata_requires_approval
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
                    "approved": False,
                    "policy_decision": (
                        "hook_ask" if before_tool_dispatch.decision is HookDecision.ASK
                        else "hook_block"
                    ),
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

        try:
            preflight = await agent._evaluate_tool_security(
                request=request,
                descriptor=descriptor,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                attempt=attempts,
                requires_approval_override=requires_approval_override,
                trusted_risk_level_override=trusted_risk_level_override,
            )
        except SecurityBoundaryError as exc:
            denied_error = str(exc).strip() or "security policy denied tool invocation"
            await agent._log_event(
                "security.policy_denied",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "code": exc.code,
                    "reason": exc.reason,
                    "error": denied_error,
                },
            )
            denied_status = "not_allow"
            await agent._emit_hook(
                HookPhase.AFTER_TOOL,
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "capability_id": request.capability_id,
                    "attempt": attempts,
                    "success": False,
                    "error": denied_error,
                    "approved": False,
                    "policy_decision": PolicyDecision.DENY.value,
                    "security_code": exc.code,
                    "evidence_collected": False,
                    "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                    "budget_stats": agent._budget_stats(),
                },
            )
            return {
                "success": False,
                "status": denied_status,
                "error": denied_error,
                "output": {
                    "status": denied_status,
                    "code": exc.code,
                    "message": denied_error,
                },
            }

        trusted_input = preflight.trusted_input
        risk_level = agent._risk_level_from_trusted_input(trusted_input)
        effective_params = dict(trusted_input.params)
        policy_decision = preflight.decision.value
        force_approval = (
            metadata_requires_approval
            or preflight.decision is PolicyDecision.APPROVE_REQUIRED
        )
        requires_approval = descriptor_requires_approval or force_approval

        if preflight.decision is PolicyDecision.DENY:
            denied_error = preflight.reason or "tool invocation denied by security policy"
            await agent._log_event(
                "security.policy_denied",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "code": SECURITY_POLICY_DENIED,
                    "reason": preflight.reason,
                },
            )
            denied_status = "not_allow"
            await agent._emit_hook(
                HookPhase.AFTER_TOOL,
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "capability_id": request.capability_id,
                    "attempt": attempts,
                    "success": False,
                    "error": denied_error,
                    "approved": False,
                    "policy_decision": policy_decision,
                    "security_code": SECURITY_POLICY_DENIED,
                    "evidence_collected": False,
                    "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                    "budget_stats": agent._budget_stats(),
                },
            )
            return {
                "success": False,
                "status": denied_status,
                "error": denied_error,
                "output": {
                    "status": denied_status,
                    "code": SECURITY_POLICY_DENIED,
                    "message": denied_error,
                },
            }

        if (
            force_approval
            and not descriptor_requires_approval
            and agent._approval_manager is None
        ):
            denied_error = "tool invocation requires approval but no approval manager is configured"
            await agent._log_event(
                "security.policy_denied",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "code": SECURITY_APPROVAL_MANAGER_MISSING,
                    "reason": "approval manager missing",
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
                    "error": denied_error,
                    "approved": False,
                    "policy_decision": policy_decision,
                    "security_code": SECURITY_APPROVAL_MANAGER_MISSING,
                    "evidence_collected": False,
                    "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                    "budget_stats": agent._budget_stats(),
                },
            )
            return {
                "success": False,
                "status": "fail",
                "error": denied_error,
                "output": {
                    "status": "fail",
                    "code": SECURITY_APPROVAL_MANAGER_MISSING,
                    "message": denied_error,
                },
            }

        await agent._log_event(
            "tool.invoke",
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "capability_id": request.capability_id,
                "attempt": attempts,
                "policy_decision": policy_decision,
            },
        )

        try:
            async def approval_observer(payload: dict[str, Any]) -> None:
                await agent._log_event(
                    "security.policy_approval",
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "capability_id": request.capability_id,
                        **payload,
                    },
                )

            approval_ctx = ApprovalInvokeContext(
                session_id=session_id,
                transport=transport,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                event_logger=agent._log_event,
                runtime_context=agent._context,
                force_approval=force_approval,
                approval_reason=(
                    preflight.reason
                    if preflight.decision is PolicyDecision.APPROVE_REQUIRED
                    else None
                ),
                approval_observer=approval_observer,
            )
            result = await agent._security_boundary.execute_safe(
                action="invoke_tool",
                fn=lambda: agent._governed_tool_gateway.invoke(
                    request.capability_id,
                    approval_ctx,
                    envelope=request.envelope,
                    **effective_params,
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
                    "policy_decision": policy_decision,
                },
            )

            tool_success = True
            if hasattr(result, "success") and not result.success:
                tool_success = False
            evidence_collected = bool(getattr(result, "evidence", []))
            denied_output = getattr(result, "output", {})
            # Derive "approved" from both the pre-invocation policy decision
            # AND the runtime approval outcome.  When policy_decision is
            # "approve_required", the GovernedToolGateway may still deny at
            # runtime (returning output.status="not_allow"), so we must also
            # check the tool result for an explicit denial signal.
            approved = policy_decision != PolicyDecision.DENY.value
            if not tool_success and isinstance(denied_output, dict):
                if denied_output.get("status") == "not_allow":
                    approved = False
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
                    "policy_decision": policy_decision,
                    "evidence_collected": evidence_collected,
                    "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                    "budget_stats": agent._budget_stats(),
                },
            )

            if not tool_success:
                tool_fail_status = "fail"
                if isinstance(denied_output, dict):
                    candidate = denied_output.get("status")
                    if isinstance(candidate, str) and candidate:
                        tool_fail_status = candidate
                return {
                    "success": False,
                    "status": tool_fail_status,
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

        except Exception as exc:
            await agent._log_event(
                "tool.error",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": request.capability_id,
                    "error": str(exc),
                    "attempt": attempts,
                    "policy_decision": policy_decision,
                },
            )
            # Derive approved from the policy decision made before execution,
            # not from the exception type.  Infra errors do not revoke approval.
            approved = policy_decision != PolicyDecision.DENY.value
            from dare_framework.tool.exceptions import HumanApprovalRequired

            if isinstance(exc, HumanApprovalRequired):
                approved = False
            await agent._emit_hook(
                HookPhase.AFTER_TOOL,
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "capability_id": request.capability_id,
                    "attempt": attempts,
                    "success": False,
                    "error": str(exc),
                    "approved": approved,
                    "policy_decision": policy_decision,
                    "evidence_collected": False,
                    "duration_ms": (time.perf_counter() - tool_start) * 1000.0,
                    "budget_stats": agent._budget_stats(),
                },
            )
            return {
                "success": False,
                "status": "fail",
                "error": str(exc),
                "output": {},
            }


def _done_predicate_satisfied(done_predicate: DonePredicate, result: Any) -> bool:
    required_keys = list(done_predicate.required_keys or [])
    if not required_keys:
        return True
    output = getattr(result, "output", None)
    if not isinstance(output, dict):
        return False
    return all(key in output for key in required_keys)
