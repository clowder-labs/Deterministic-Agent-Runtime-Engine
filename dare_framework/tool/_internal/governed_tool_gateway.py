"""Gateway-level tool invocation governance (approval + execution).

This module keeps policy/approval decisions at the tool invocation boundary so
agent orchestration can focus on the loop itself.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalEvaluationStatus,
    ToolApprovalManager,
)
from dare_framework.tool.kernel import IToolGateway
from dare_framework.tool.types import CapabilityDescriptor, ToolResult
from dare_framework.transport.interaction.payloads import build_approval_pending_payload
from dare_framework.transport.types import (
    EnvelopeKind,
    TransportEnvelope,
    TransportEventType,
    new_envelope_id,
)

if TYPE_CHECKING:
    from dare_framework.context import Context
    from dare_framework.plan.types import Envelope
    from dare_framework.transport.kernel import AgentChannel

ApprovalEventLogger = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class ApprovalInvokeContext:
    """Gateway-local approval governance context carried outside tool params."""

    session_id: str | None = None
    transport: AgentChannel | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    event_logger: ApprovalEventLogger | None = None


class GovernedToolGateway(IToolGateway):
    """IToolGateway wrapper that applies approval memory before tool execution."""

    def __init__(
        self,
        delegate: IToolGateway,
        *,
        approval_manager: ToolApprovalManager | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._delegate = delegate
        self._approval_manager = approval_manager
        self._logger = logger or logging.getLogger("dare.tool.governed_gateway")

    def list_capabilities(self) -> list[CapabilityDescriptor]:
        return self._delegate.list_capabilities()

    async def invoke(
        self,
        capability_id: str,
        approval: ApprovalInvokeContext | None = None,
        *,
        envelope: Envelope,
        context: Context | None = None,
        **params: Any,
    ) -> ToolResult:
        session_id = approval.session_id if approval is not None else None
        transport = approval.transport if approval is not None else None
        tool_name = approval.tool_name if approval is not None else None
        tool_call_id = approval.tool_call_id if approval is not None else None
        approval_event_logger = approval.event_logger if approval is not None else None

        requires_approval = self._requires_approval(capability_id)
        if requires_approval:
            decision_error = await self._resolve_approval(
                capability_id=capability_id,
                params=params,
                session_id=session_id,
                transport=transport,
                tool_name=tool_name or capability_id,
                tool_call_id=tool_call_id or "unknown",
                event_logger=approval_event_logger,
            )
            if decision_error is not None:
                # Return a deterministic denied result so orchestrators can treat
                # it as a normal tool outcome instead of a special side channel.
                return ToolResult(
                    success=False,
                    output={"status": "not_allow"},
                    error=decision_error,
                )

        result = await self._delegate.invoke(
            capability_id,
            envelope=envelope,
            context=context,
            **params,
        )
        return result

    def _requires_approval(self, capability_id: str) -> bool:
        descriptor = self._find_capability(capability_id)
        if descriptor is None:
            return False
        metadata = descriptor.metadata
        return bool(metadata and metadata.get("requires_approval", False))

    def _find_capability(self, capability_id: str) -> CapabilityDescriptor | None:
        for descriptor in self._delegate.list_capabilities():
            if descriptor.id == capability_id:
                return descriptor
        return None

    async def _resolve_approval(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        transport: AgentChannel | None,
        tool_name: str,
        tool_call_id: str,
        event_logger: ApprovalEventLogger | None,
    ) -> str | None:
        if self._approval_manager is None:
            return "tool requires approval but no approval manager is configured"

        evaluation = await self._approval_manager.evaluate(
            capability_id=capability_id,
            params=params,
            session_id=session_id,
            reason=f"Tool {capability_id} requires approval",
        )
        if evaluation.status == ApprovalEvaluationStatus.ALLOW:
            await self._emit_approval_event(
                event_logger,
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
            return None
        if evaluation.status == ApprovalEvaluationStatus.DENY:
            await self._emit_approval_event(
                event_logger,
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
            return "tool invocation denied by approval rule"
        if evaluation.request is None:
            return "tool invocation requires approval"

        request_id = evaluation.request.request_id
        await self._emit_approval_pending_message(
            request=evaluation.request.to_dict(),
            transport=transport,
            capability_id=capability_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )
        await self._emit_approval_event(
            event_logger,
            "exec.waiting_human",
            {
                "checkpoint_id": request_id,
                "reason": evaluation.request.reason,
                "mode": "approval_memory_wait",
            },
        )
        decision = await self._approval_manager.wait_for_resolution(request_id)
        await self._emit_approval_event(
            event_logger,
            "exec.resume",
            {
                "checkpoint_id": request_id,
                "decision": decision.value,
            },
        )
        await self._emit_approval_event(
            event_logger,
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
        if decision == ApprovalDecision.ALLOW:
            return None
        return "tool invocation denied by human approval"

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
        # Approval pending is an explicit user-choice interaction shape.
        resp = payload.get("resp")
        if isinstance(resp, dict):
            resp.setdefault(
                "options",
                [
                    {"label": "allow", "description": "Approve this tool invocation."},
                    {"label": "deny", "description": "Deny this tool invocation."},
                ],
            )

        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.SELECT,
            event_type=TransportEventType.APPROVAL_PENDING.value,
            payload=payload,
        )
        try:
            await transport.send(envelope)
        except Exception:
            self._logger.exception("approval pending transport send failed")

    async def _emit_approval_event(
        self,
        event_logger: ApprovalEventLogger | None,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        if event_logger is None:
            return
        try:
            await event_logger(event_type, payload)
        except Exception:
            self._logger.exception("approval event emission failed: %s", event_type)


__all__ = ["ApprovalInvokeContext", "GovernedToolGateway"]
