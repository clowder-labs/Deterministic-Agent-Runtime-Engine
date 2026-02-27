from __future__ import annotations

from typing import Any

import pytest

from dare_framework.plan.types import Envelope
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalEvaluation,
    ApprovalEvaluationStatus,
    PendingApprovalRequest,
)
from dare_framework.tool._internal.governed_tool_gateway import (
    ApprovalInvokeContext,
    GovernedToolGateway,
)
from dare_framework.tool.types import CapabilityDescriptor, CapabilityType, ToolResult


class _RecordingDelegateGateway:
    def __init__(self, capability: CapabilityDescriptor) -> None:
        self._capability = capability
        self.invoke_calls: list[dict[str, Any]] = []

    def list_capabilities(self) -> list[CapabilityDescriptor]:
        return [self._capability]

    async def invoke(self, capability_id: str, *, envelope: Envelope, **params: Any) -> ToolResult:
        self.invoke_calls.append(
            {
                "capability_id": capability_id,
                "envelope": envelope,
                "params": dict(params),
            }
        )
        return ToolResult(success=True, output={"ok": True})


class _RecordingApprovalManager:
    def __init__(self) -> None:
        self.evaluate_calls: list[dict[str, Any]] = []

    async def evaluate(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        reason: str,
    ) -> ApprovalEvaluation:
        self.evaluate_calls.append(
            {
                "capability_id": capability_id,
                "params": dict(params),
                "session_id": session_id,
                "reason": reason,
            }
        )
        return ApprovalEvaluation(status=ApprovalEvaluationStatus.ALLOW)


class _PendingApprovalManager(_RecordingApprovalManager):
    async def evaluate(
        self,
        *,
        capability_id: str,
        params: dict[str, Any],
        session_id: str | None,
        reason: str,
    ) -> ApprovalEvaluation:
        self.evaluate_calls.append(
            {
                "capability_id": capability_id,
                "params": dict(params),
                "session_id": session_id,
                "reason": reason,
            }
        )
        request = PendingApprovalRequest(
            request_id="req-1",
            capability_id=capability_id,
            params=dict(params),
            params_hash="hash",
            command=None,
            session_id=session_id,
            reason=reason,
            created_at=1.0,
        )
        return ApprovalEvaluation(status=ApprovalEvaluationStatus.PENDING, request=request)

    async def wait_for_resolution(self, request_id: str) -> ApprovalDecision:
        assert request_id == "req-1"
        return ApprovalDecision.ALLOW


@pytest.mark.asyncio
async def test_governed_gateway_approval_uses_effective_params_with_context_collision() -> None:
    capability = CapabilityDescriptor(
        id="run_command",
        type=CapabilityType.TOOL,
        name="run_command",
        description="run command",
        input_schema={"type": "object", "properties": {}},
        metadata={"requires_approval": True},
    )
    delegate = _RecordingDelegateGateway(capability)
    approval_manager = _RecordingApprovalManager()
    gateway = GovernedToolGateway(delegate, approval_manager=approval_manager)

    runtime_context = object()
    envelope = Envelope()
    result = await gateway.invoke(
        capability.id,
        approval=ApprovalInvokeContext(runtime_context=runtime_context),
        envelope=envelope,
        command="echo hello",
        context="tool-arg-context",
    )

    assert result.success is True
    assert approval_manager.evaluate_calls
    assert approval_manager.evaluate_calls[0]["params"] == {
        "command": "echo hello",
        "context": "tool-arg-context",
    }

    assert delegate.invoke_calls
    delegate_params = delegate.invoke_calls[0]["params"]
    assert delegate_params["command"] == "echo hello"
    assert delegate_params["context"] == "tool-arg-context"


@pytest.mark.asyncio
async def test_governed_gateway_force_approval_uses_custom_reason_and_observer() -> None:
    capability = CapabilityDescriptor(
        id="run_command",
        type=CapabilityType.TOOL,
        name="run_command",
        description="run command",
        input_schema={"type": "object", "properties": {}},
        metadata={"requires_approval": False},
    )
    delegate = _RecordingDelegateGateway(capability)
    approval_manager = _PendingApprovalManager()
    gateway = GovernedToolGateway(delegate, approval_manager=approval_manager)
    observed: list[dict[str, Any]] = []

    async def observer(payload: dict[str, Any]) -> None:
        observed.append(dict(payload))

    result = await gateway.invoke(
        capability.id,
        approval=ApprovalInvokeContext(
            force_approval=True,
            approval_reason="policy requires approval",
            approval_observer=observer,
        ),
        envelope=Envelope(),
        command="echo hello",
    )

    assert result.success is True
    assert approval_manager.evaluate_calls
    assert approval_manager.evaluate_calls[0]["reason"] == "policy requires approval"
    assert any(item.get("status") == "pending" and item.get("request_id") == "req-1" for item in observed)
    assert any(item.get("status") == "allow" and item.get("request_id") == "req-1" for item in observed)
