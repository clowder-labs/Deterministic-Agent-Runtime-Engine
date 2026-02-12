from __future__ import annotations

import asyncio

import pytest

from dare_framework.tool.action_handler import ApprovalsActionHandler
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalMatcherKind,
    ApprovalScope,
    JsonApprovalRuleStore,
    ToolApprovalManager,
)
from dare_framework.transport.interaction.resource_action import ResourceAction


@pytest.fixture
def manager(tmp_path):
    workspace_store = JsonApprovalRuleStore(tmp_path / "workspace" / "approvals.json")
    user_store = JsonApprovalRuleStore(tmp_path / "user" / "approvals.json")
    return ToolApprovalManager(workspace_store=workspace_store, user_store=user_store)


@pytest.mark.asyncio
async def test_approvals_action_handler_list_and_grant(manager) -> None:
    handler = ApprovalsActionHandler(manager)

    first = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status"},
        session_id="session-a",
        reason="Tool run_command requires approval",
    )
    assert first.request is not None

    listed = await handler.invoke(ResourceAction.APPROVALS_LIST)
    pending = listed["pending"]
    assert len(pending) == 1
    assert pending[0]["request_id"] == first.request.request_id

    wait_task = asyncio.create_task(manager.wait_for_resolution(first.request.request_id))
    granted = await handler.invoke(
        ResourceAction.APPROVALS_GRANT,
        request_id=first.request.request_id,
        scope=ApprovalScope.WORKSPACE.value,
        matcher=ApprovalMatcherKind.EXACT_PARAMS.value,
    )
    assert granted["request_id"] == first.request.request_id
    assert granted["rule"] is not None

    assert await wait_task == ApprovalDecision.ALLOW


@pytest.mark.asyncio
async def test_approvals_action_handler_revoke_rule(manager) -> None:
    handler = ApprovalsActionHandler(manager)

    first = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status"},
        session_id="session-b",
        reason="Tool run_command requires approval",
    )
    assert first.request is not None

    wait_task = asyncio.create_task(manager.wait_for_resolution(first.request.request_id))
    granted = await handler.invoke(
        ResourceAction.APPROVALS_GRANT,
        request_id=first.request.request_id,
        scope=ApprovalScope.WORKSPACE.value,
        matcher=ApprovalMatcherKind.EXACT_PARAMS.value,
    )
    assert await wait_task == ApprovalDecision.ALLOW

    rule = granted["rule"]
    revoked = await handler.invoke(ResourceAction.APPROVALS_REVOKE, rule_id=rule["rule_id"])
    assert revoked["removed"] is True


@pytest.mark.asyncio
async def test_approvals_action_handler_poll_returns_pending_request(manager) -> None:
    handler = ApprovalsActionHandler(manager)

    first = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status --short"},
        session_id="session-poll",
        reason="Tool run_command requires approval",
    )
    assert first.request is not None

    polled = await handler.invoke(ResourceAction.APPROVALS_POLL)
    request = polled["request"]
    assert isinstance(request, dict)
    assert request["request_id"] == first.request.request_id


@pytest.mark.asyncio
async def test_approvals_action_handler_poll_timeout_returns_null_request(manager) -> None:
    handler = ApprovalsActionHandler(manager)

    polled = await handler.invoke(ResourceAction.APPROVALS_POLL, timeout_seconds=0.05)
    assert polled["request"] is None


@pytest.mark.asyncio
async def test_approvals_action_handler_poll_filters_by_session_id(manager) -> None:
    handler = ApprovalsActionHandler(manager)
    first = await manager.evaluate(
        capability_id="run_command",
        params={"command": "echo session-a"},
        session_id="session-a",
        reason="Tool run_command requires approval",
    )
    second = await manager.evaluate(
        capability_id="run_command",
        params={"command": "echo session-b"},
        session_id="session-b",
        reason="Tool run_command requires approval",
    )
    assert first.request is not None
    assert second.request is not None

    polled = await handler.invoke(ResourceAction.APPROVALS_POLL, session_id="session-b")
    request = polled["request"]
    assert isinstance(request, dict)
    assert request["request_id"] == second.request.request_id
