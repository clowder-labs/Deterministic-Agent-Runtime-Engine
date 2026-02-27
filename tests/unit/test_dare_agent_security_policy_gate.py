from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from dare_framework.agent.dare_agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.plan.types import ToolLoopRequest
from dare_framework.security.errors import SECURITY_POLICY_DENIED
from dare_framework.security.kernel import ISecurityBoundary
from dare_framework.security.types import PolicyDecision, RiskLevel, SandboxSpec, TrustedInput
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalMatcherKind,
    ApprovalScope,
    JsonApprovalRuleStore,
    ToolApprovalManager,
)
from dare_framework.tool.types import CapabilityDescriptor, CapabilityType, ToolResult


class _Model:
    name = "mock-model"

    async def generate(self, model_input: Any, *, options: Any = None) -> Any:
        _ = (model_input, options)
        raise RuntimeError("generate should not be called in tool-loop tests")


class _RecordingEventLog:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def append(self, event_type: str, payload: dict[str, Any]) -> str:
        self.events.append((event_type, dict(payload)))
        return f"evt-{len(self.events)}"


class _RecordingGateway:
    def __init__(self, capabilities: list[CapabilityDescriptor] | None = None) -> None:
        self._capabilities = list(capabilities or [])
        self.invoke_calls: list[dict[str, Any]] = []

    def list_capabilities(self) -> list[CapabilityDescriptor]:
        return list(self._capabilities)

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        self.invoke_calls.append({"capability_id": capability_id, "envelope": envelope, "params": dict(params)})
        return ToolResult(success=True, output={"ok": True})


class _FixedBoundary(ISecurityBoundary):
    def __init__(self, decision: PolicyDecision) -> None:
        self._decision = decision
        self.calls: list[str] = []

    async def verify_trust(self, *, input: dict[str, Any], context: dict[str, Any]) -> TrustedInput:
        self.calls.append("verify_trust")
        return TrustedInput(
            params=dict(input),
            risk_level=RiskLevel.READ_ONLY,
            metadata={"capability_id": context.get("capability_id"), "requires_approval": False},
        )

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        _ = (action, resource, context)
        self.calls.append("check_policy")
        return self._decision

    async def execute_safe(
        self,
        *,
        action: str,
        fn: Any,
        sandbox: SandboxSpec,
    ) -> Any:
        _ = (action, sandbox)
        return await fn()


def _agent(
    *,
    gateway: _RecordingGateway,
    event_log: _RecordingEventLog | None = None,
    security_boundary: ISecurityBoundary | None = None,
    approval_manager: ToolApprovalManager | None = None,
) -> DareAgent:
    agent = DareAgent(
        name="security-agent",
        model=_Model(),
        context=Context(config=Config()),
        tool_gateway=gateway,
        event_log=event_log,
        security_boundary=security_boundary,
        approval_manager=approval_manager,
    )
    # _run_tool_loop is normally called inside execute(), where session state
    # is always initialized. Unit tests call it directly.
    agent._session_state = type(  # noqa: SLF001 - targeted runtime unit test setup
        "_SessionState",
        (),
        {"run_id": "run-security", "task_id": "task-security", "current_milestone_state": None},
    )()
    return agent


def _descriptor(*, requires_approval: bool = False) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        id="run_command",
        type=CapabilityType.TOOL,
        name="run_command",
        description="Run shell command",
        input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
        metadata={"requires_approval": requires_approval, "risk_level": "read_only"},
    )


@pytest.mark.asyncio
async def test_security_preflight_allow_invokes_gateway() -> None:
    event_log = _RecordingEventLog()
    boundary = _FixedBoundary(PolicyDecision.ALLOW)
    gateway = _RecordingGateway([_descriptor()])
    agent = _agent(gateway=gateway, event_log=event_log, security_boundary=boundary)

    result = await agent._run_tool_loop(  # noqa: SLF001 - direct runtime boundary coverage
        ToolLoopRequest(capability_id="run_command", params={"command": "echo ok"}),
        tool_name="run_command",
        tool_call_id="tc-allow",
        descriptor=_descriptor(),
    )

    assert result["success"] is True
    assert boundary.calls == ["verify_trust", "check_policy"]
    assert len(gateway.invoke_calls) == 1
    event_types = [event_type for event_type, _ in event_log.events]
    assert "security.trust_verified" in event_types
    assert "security.policy_checked" in event_types
    trust_payload = next(payload for event_type, payload in event_log.events if event_type == "security.trust_verified")
    policy_payload = next(payload for event_type, payload in event_log.events if event_type == "security.policy_checked")
    assert trust_payload["capability_id"] == "run_command"
    assert policy_payload["capability_id"] == "run_command"
    assert policy_payload["decision"] == PolicyDecision.ALLOW.value


@pytest.mark.asyncio
async def test_security_preflight_deny_blocks_gateway() -> None:
    event_log = _RecordingEventLog()
    boundary = _FixedBoundary(PolicyDecision.DENY)
    gateway = _RecordingGateway([_descriptor()])
    agent = _agent(gateway=gateway, event_log=event_log, security_boundary=boundary)

    result = await agent._run_tool_loop(  # noqa: SLF001 - direct runtime boundary coverage
        ToolLoopRequest(capability_id="run_command", params={"command": "echo no"}),
        tool_name="run_command",
        tool_call_id="tc-deny",
        descriptor=_descriptor(),
    )

    assert result["success"] is False
    assert result["status"] == "not_allow"
    assert result["output"]["code"] == SECURITY_POLICY_DENIED
    assert gateway.invoke_calls == []


@pytest.mark.asyncio
async def test_security_preflight_approve_required_routes_to_approval_memory(tmp_path: Path) -> None:
    event_log = _RecordingEventLog()
    boundary = _FixedBoundary(PolicyDecision.APPROVE_REQUIRED)
    gateway = _RecordingGateway([_descriptor(requires_approval=False)])
    approval_manager = ToolApprovalManager(
        workspace_store=JsonApprovalRuleStore(tmp_path / "workspace" / "approvals.json"),
        user_store=JsonApprovalRuleStore(tmp_path / "user" / "approvals.json"),
    )
    agent = _agent(
        gateway=gateway,
        event_log=event_log,
        security_boundary=boundary,
        approval_manager=approval_manager,
    )

    run_task = asyncio.create_task(
        agent._run_tool_loop(  # noqa: SLF001 - direct runtime boundary coverage
            ToolLoopRequest(capability_id="run_command", params={"command": "echo gated"}),
            tool_name="run_command",
            tool_call_id="tc-approve",
            descriptor=_descriptor(requires_approval=False),
        )
    )
    request_id: str | None = None
    for _ in range(100):
        pending = approval_manager.list_pending()
        if pending:
            request_id = pending[0].request_id
            break
        await asyncio.sleep(0.01)
    assert request_id is not None

    await approval_manager.grant(
        request_id,
        scope=ApprovalScope.ONCE,
        matcher=ApprovalMatcherKind.EXACT_PARAMS,
    )
    result = await run_task

    assert result["success"] is True
    assert len(gateway.invoke_calls) == 1
    approval_events = [payload for event_type, payload in event_log.events if event_type == "security.policy_approval"]
    assert approval_events
    assert any(isinstance(payload.get("request_id"), str) for payload in approval_events)


@pytest.mark.asyncio
async def test_missing_explicit_boundary_uses_default_preflight_instead_of_bypass() -> None:
    event_log = _RecordingEventLog()
    gateway = _RecordingGateway([_descriptor()])
    agent = _agent(gateway=gateway, event_log=event_log, security_boundary=None)

    result = await agent._run_tool_loop(  # noqa: SLF001 - direct runtime boundary coverage
        ToolLoopRequest(capability_id="run_command", params={"command": "echo default"}),
        tool_name="run_command",
        tool_call_id="tc-default",
        descriptor=_descriptor(),
    )

    assert result["success"] is True
    event_types = [event_type for event_type, _ in event_log.events]
    assert "security.trust_verified" in event_types
    assert "security.policy_checked" in event_types
