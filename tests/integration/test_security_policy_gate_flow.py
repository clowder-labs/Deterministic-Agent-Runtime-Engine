from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from dare_framework.agent.dare_agent import DareAgent
from dare_framework.config import Config
from dare_framework.context import Context
from dare_framework.model.types import ModelInput, ModelResponse
from dare_framework.security.impl import PolicySecurityBoundary
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalMatcherKind,
    ApprovalScope,
    JsonApprovalRuleStore,
    ToolApprovalManager,
)
from dare_framework.tool.types import CapabilityDescriptor, CapabilityType, ToolResult


class _TwoStepModel:
    name = "two-step-model"

    def __init__(self) -> None:
        self._responses = [
            ModelResponse(
                content="run high-risk command",
                tool_calls=[{"name": "run_command", "arguments": {"command": "echo hi"}}],
            ),
            ModelResponse(content="done", tool_calls=[]),
        ]

    async def generate(self, model_input: ModelInput, *, options: Any = None) -> ModelResponse:
        _ = (model_input, options)
        if self._responses:
            return self._responses.pop(0)
        return ModelResponse(content="done", tool_calls=[])


class _RecordingGateway:
    def __init__(
        self,
        *,
        risk_level: str = "non_idempotent_effect",
        requires_approval: bool = False,
    ) -> None:
        self.invoke_calls: list[dict[str, Any]] = []
        self._descriptor = CapabilityDescriptor(
            id="run_command",
            type=CapabilityType.TOOL,
            name="run_command",
            description="Run shell command",
            input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
            metadata={
                "risk_level": risk_level,
                "requires_approval": requires_approval,
            },
        )

    def list_capabilities(self) -> list[CapabilityDescriptor]:
        return [self._descriptor]

    async def invoke(self, capability_id: str, *, envelope: Any, **params: Any) -> ToolResult[dict[str, Any]]:
        self.invoke_calls.append(
            {"capability_id": capability_id, "envelope": envelope, "params": dict(params)}
        )
        return ToolResult(success=True, output={"ok": True})


@pytest.mark.asyncio
async def test_high_risk_tool_invocation_must_pass_policy_gate(tmp_path: Path) -> None:
    approval_manager = ToolApprovalManager(
        workspace_store=JsonApprovalRuleStore(tmp_path / "workspace" / "approvals.json"),
        user_store=JsonApprovalRuleStore(tmp_path / "user" / "approvals.json"),
    )
    gateway = _RecordingGateway()
    agent = DareAgent(
        name="security-policy-gate-flow",
        model=_TwoStepModel(),
        context=Context(config=Config()),
        tool_gateway=gateway,
        approval_manager=approval_manager,
        security_boundary=PolicySecurityBoundary(),
    )

    run_task = asyncio.create_task(agent("run high risk tool"))
    request_id: str | None = None
    for _ in range(100):
        pending = approval_manager.list_pending()
        if pending:
            request_id = pending[0].request_id
            break
        await asyncio.sleep(0.01)

    assert request_id is not None
    assert gateway.invoke_calls == []

    await approval_manager.grant(
        request_id,
        scope=ApprovalScope.ONCE,
        matcher=ApprovalMatcherKind.EXACT_PARAMS,
    )
    result = await run_task

    assert result.success is True
    assert len(gateway.invoke_calls) == 1


@pytest.mark.asyncio
async def test_read_only_tool_invocation_bypasses_pending_approval(tmp_path: Path) -> None:
    approval_manager = ToolApprovalManager(
        workspace_store=JsonApprovalRuleStore(tmp_path / "workspace" / "approvals.json"),
        user_store=JsonApprovalRuleStore(tmp_path / "user" / "approvals.json"),
    )
    gateway = _RecordingGateway(risk_level="read_only")
    agent = DareAgent(
        name="security-policy-gate-flow-allow",
        model=_TwoStepModel(),
        context=Context(config=Config()),
        tool_gateway=gateway,
        approval_manager=approval_manager,
        security_boundary=PolicySecurityBoundary(),
    )

    result = await agent("run read only tool")

    assert result.success is True
    assert len(gateway.invoke_calls) == 1
    assert approval_manager.list_pending() == []


@pytest.mark.asyncio
async def test_denied_capability_blocks_tool_before_invocation(tmp_path: Path) -> None:
    approval_manager = ToolApprovalManager(
        workspace_store=JsonApprovalRuleStore(tmp_path / "workspace" / "approvals.json"),
        user_store=JsonApprovalRuleStore(tmp_path / "user" / "approvals.json"),
    )
    gateway = _RecordingGateway(risk_level="read_only")
    agent = DareAgent(
        name="security-policy-gate-flow-deny",
        model=_TwoStepModel(),
        context=Context(config=Config()),
        tool_gateway=gateway,
        approval_manager=approval_manager,
        security_boundary=PolicySecurityBoundary(deny_capability_ids={"run_command"}),
    )

    result = await agent("run denied tool")

    tool_messages = [msg for msg in agent._context.stm_get() if msg.role == "tool"]  # noqa: SLF001
    assert tool_messages
    tool_payload = json.loads(tool_messages[-1].content)
    assert tool_payload.get("status") == "not_allow"
    assert tool_payload.get("success") is False
    assert gateway.invoke_calls == []
    assert approval_manager.list_pending() == []
    assert result.success is True
