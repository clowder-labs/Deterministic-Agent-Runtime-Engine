"""Gateway-level tool invocation governance (approval + execution).

This module keeps policy/approval decisions at the tool invocation boundary so
agent orchestration can focus on the loop itself.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Literal

from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalEvaluationStatus,
    ToolApprovalManager,
)
from dare_framework.tool._internal.runtime_context_override import (
    RUNTIME_CONTEXT_PARAM,
    RuntimeContextOverride,
)
from dare_framework.tool.kernel import IToolGateway
from dare_framework.tool.types import CapabilityDescriptor, ToolResult
from dare_framework.transport.interaction.payloads import build_approval_pending_payload
from dare_framework.transport.types import (
    EnvelopeKind,
    TransportEnvelope,
    new_envelope_id,
)

if TYPE_CHECKING:
    from dare_framework.context import Context
    from dare_framework.plan.types import Envelope
    from dare_framework.transport.kernel import AgentChannel

ApprovalEventLogger = Callable[[str, dict[str, Any]], Awaitable[None]]
ApprovalObserver = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class ApprovalInvokeContext:
    """Gateway-local approval governance context carried outside tool params."""

    session_id: str | None = None
    transport: AgentChannel | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    event_logger: ApprovalEventLogger | None = None
    runtime_context: Context | None = None
    force_approval: bool = False
    approval_reason: str | None = None
    approval_observer: ApprovalObserver | None = None


@dataclass(frozen=True)
class ApprovalResolution:
    """Approval decision normalized for invoke-layer status mapping."""

    verdict: Literal["allow", "deny", "error"]
    error: str | None = None


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
        self._runtime_context_param = RUNTIME_CONTEXT_PARAM

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
        runtime_context = approval.runtime_context if approval is not None else None
        force_approval = approval.force_approval if approval is not None else False
        approval_reason = approval.approval_reason if approval is not None else None
        approval_observer = approval.approval_observer if approval is not None else None
        if runtime_context is None:
            runtime_context = context

        delegate_params = params
        if approval is not None and approval.runtime_context is not None and context is not None:
            # When callers pass tool argument key `context`, Python binds it to this
            # named parameter. Re-inject it into tool params so schema-defined
            # arguments are preserved while runtime context stays out-of-band.
            delegate_params = dict(params)
            delegate_params.setdefault("context", context)

        requires_approval = force_approval or self._requires_approval(capability_id)
        if requires_approval:
            approval_resolution = await self._resolve_approval(
                capability_id=capability_id,
                params=dict(delegate_params),
                session_id=session_id,
                transport=transport,
                tool_name=tool_name or capability_id,
                tool_call_id=tool_call_id or "unknown",
                approval_reason=approval_reason,
                approval_observer=approval_observer,
                event_logger=approval_event_logger,
            )
            if approval_resolution.verdict != "allow":
                status = "not_allow" if approval_resolution.verdict == "deny" else "fail"
                error = approval_resolution.error or "approval check failed"
                return ToolResult(
                    success=False,
                    output={"status": status},
                    error=error,
                )

        result = await self._delegate.invoke(
            capability_id,
            envelope=envelope,
            **self._build_delegate_invoke_kwargs(
                runtime_context=runtime_context,
                params=delegate_params,
            ),
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
        approval_reason: str | None,
        approval_observer: ApprovalObserver | None,
        event_logger: ApprovalEventLogger | None,
    ) -> ApprovalResolution:
        if self._approval_manager is None:
            return ApprovalResolution(
                verdict="error",
                error="tool requires approval but no approval manager is configured",
            )

        try:
            # Keep a stable error prefix so agent-level callers can reason about
            # approval failures deterministically.
            evaluation = await self._approval_manager.evaluate(
                capability_id=capability_id,
                params=params,
                session_id=session_id,
                reason=approval_reason or f"Tool {capability_id} requires approval",
            )
        except Exception as exc:
            await self._emit_approval_event(
                event_logger,
                "tool.approval",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": capability_id,
                    "status": "error",
                    "source": "evaluate",
                    "error": str(exc),
                },
            )
            await self._notify_approval_observer(
                approval_observer,
                {
                    "status": "error",
                    "source": "evaluate",
                    "error": str(exc),
                },
            )
            return ApprovalResolution(
                verdict="error",
                error=f"tool approval evaluation failed: {exc}",
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
            await self._notify_approval_observer(
                approval_observer,
                {
                    "status": "allow",
                    "source": "rule",
                    "rule_id": evaluation.rule.rule_id if evaluation.rule is not None else None,
                },
            )
            return ApprovalResolution(verdict="allow")
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
            await self._notify_approval_observer(
                approval_observer,
                {
                    "status": "deny",
                    "source": "rule",
                    "rule_id": evaluation.rule.rule_id if evaluation.rule is not None else None,
                },
            )
            return ApprovalResolution(
                verdict="deny",
                error="tool invocation denied by approval rule",
            )
        if evaluation.request is None:
            return ApprovalResolution(
                verdict="error",
                error="tool invocation requires approval",
            )

        request_id = evaluation.request.request_id
        await self._notify_approval_observer(
            approval_observer,
            {
                "status": "pending",
                "source": "pending_request",
                "request_id": request_id,
            },
        )
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
        try:
            decision = await self._approval_manager.wait_for_resolution(request_id)
        except Exception as exc:
            await self._emit_approval_event(
                event_logger,
                "tool.approval",
                {
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "capability_id": capability_id,
                    "status": "error",
                    "source": "pending_request",
                    "request_id": request_id,
                    "error": str(exc),
                },
            )
            await self._notify_approval_observer(
                approval_observer,
                {
                    "status": "error",
                    "source": "pending_request",
                    "request_id": request_id,
                    "error": str(exc),
                },
            )
            return ApprovalResolution(
                verdict="error",
                error=f"tool approval resolution failed: {exc}",
            )
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
        await self._notify_approval_observer(
            approval_observer,
            {
                "status": decision.value,
                "source": "pending_request",
                "request_id": request_id,
            },
        )
        if decision == ApprovalDecision.ALLOW:
            return ApprovalResolution(verdict="allow")
        return ApprovalResolution(
            verdict="deny",
            error="tool invocation denied by human approval",
        )

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
        envelope = TransportEnvelope(
            id=new_envelope_id(),
            kind=EnvelopeKind.SELECT,
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

    async def _notify_approval_observer(
        self,
        observer: ApprovalObserver | None,
        payload: dict[str, Any],
    ) -> None:
        if observer is None:
            return
        try:
            await observer(payload)
        except Exception:
            self._logger.exception("approval observer callback failed")

    def _build_delegate_invoke_kwargs(
        self,
        *,
        runtime_context: Context | None,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Assemble delegate invoke kwargs without colliding with tool arg keys."""
        kwargs: dict[str, Any] = {
            "params": dict(params),
        }
        delegate_params: dict[str, Any] = kwargs["params"]

        if runtime_context is None:
            return delegate_params

        if "context" in delegate_params:
            delegate_params[self._runtime_context_param] = RuntimeContextOverride(runtime_context)
            return delegate_params

        delegate_params["context"] = runtime_context
        return delegate_params


__all__ = ["ApprovalInvokeContext", "ApprovalResolution", "GovernedToolGateway"]
