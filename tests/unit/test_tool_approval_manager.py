from __future__ import annotations

import asyncio
import contextlib
import json

import pytest

from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalEvaluationStatus,
    ApprovalMatcherKind,
    ApprovalScope,
    JsonApprovalRuleStore,
    ToolApprovalManager,
)


@pytest.fixture
def manager(tmp_path):
    workspace_store = JsonApprovalRuleStore(tmp_path / "workspace" / "approvals.json")
    user_store = JsonApprovalRuleStore(tmp_path / "user" / "approvals.json")
    return ToolApprovalManager(workspace_store=workspace_store, user_store=user_store)


@pytest.mark.asyncio
async def test_workspace_exact_params_rule_auto_allows_repeated_call(manager, tmp_path) -> None:
    evaluation = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status --short", "cwd": "/repo"},
        session_id="session-1",
        reason="Tool run_command requires approval",
    )
    assert evaluation.status == ApprovalEvaluationStatus.PENDING
    assert evaluation.request is not None

    request_id = evaluation.request.request_id
    wait_task = asyncio.create_task(manager.wait_for_resolution(request_id))

    rule = await manager.grant(
        request_id,
        scope=ApprovalScope.WORKSPACE,
        matcher=ApprovalMatcherKind.EXACT_PARAMS,
    )
    assert rule is not None

    decision = await wait_task
    assert decision == ApprovalDecision.ALLOW

    second = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status --short", "cwd": "/repo"},
        session_id="session-2",
        reason="Tool run_command requires approval",
    )
    assert second.status == ApprovalEvaluationStatus.ALLOW

    persisted = json.loads((tmp_path / "workspace" / "approvals.json").read_text(encoding="utf-8"))
    assert len(persisted["rules"]) == 1


@pytest.mark.asyncio
async def test_command_prefix_rule_matches_prefix_only(manager) -> None:
    first = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status --short"},
        session_id="session-1",
        reason="Tool run_command requires approval",
    )
    assert first.request is not None

    wait_task = asyncio.create_task(manager.wait_for_resolution(first.request.request_id))
    await manager.grant(
        first.request.request_id,
        scope=ApprovalScope.WORKSPACE,
        matcher=ApprovalMatcherKind.COMMAND_PREFIX,
        matcher_value="git status",
    )
    assert await wait_task == ApprovalDecision.ALLOW

    allow_eval = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status --ignored"},
        session_id="session-2",
        reason="Tool run_command requires approval",
    )
    assert allow_eval.status == ApprovalEvaluationStatus.ALLOW

    pending_eval = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git fetch --all"},
        session_id="session-2",
        reason="Tool run_command requires approval",
    )
    assert pending_eval.status == ApprovalEvaluationStatus.PENDING


@pytest.mark.asyncio
async def test_session_deny_rule_blocks_matching_calls(manager) -> None:
    first = await manager.evaluate(
        capability_id="run_command",
        params={"command": "rm -rf /tmp/demo"},
        session_id="session-x",
        reason="Tool run_command requires approval",
    )
    assert first.request is not None

    wait_task = asyncio.create_task(manager.wait_for_resolution(first.request.request_id))
    await manager.deny(
        first.request.request_id,
        scope=ApprovalScope.SESSION,
        matcher=ApprovalMatcherKind.CAPABILITY,
    )
    assert await wait_task == ApprovalDecision.DENY

    blocked = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status"},
        session_id="session-x",
        reason="Tool run_command requires approval",
    )
    assert blocked.status == ApprovalEvaluationStatus.DENY


@pytest.mark.asyncio
async def test_revoke_rule_removes_automatic_pass(manager) -> None:
    first = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status"},
        session_id="session-r",
        reason="Tool run_command requires approval",
    )
    assert first.request is not None

    wait_task = asyncio.create_task(manager.wait_for_resolution(first.request.request_id))
    rule = await manager.grant(
        first.request.request_id,
        scope=ApprovalScope.WORKSPACE,
        matcher=ApprovalMatcherKind.EXACT_PARAMS,
    )
    assert await wait_task == ApprovalDecision.ALLOW
    assert rule is not None

    assert await manager.revoke(rule.rule_id) is True

    second = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status"},
        session_id="session-r",
        reason="Tool run_command requires approval",
    )
    assert second.status == ApprovalEvaluationStatus.PENDING


@pytest.mark.asyncio
async def test_poll_pending_returns_next_request_when_available(manager) -> None:
    first = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status --short"},
        session_id="session-poll",
        reason="Tool run_command requires approval",
    )
    assert first.request is not None

    polled = await manager.poll_pending()
    assert polled is not None
    assert polled.request_id == first.request.request_id


@pytest.mark.asyncio
async def test_poll_pending_filters_by_session_id(manager) -> None:
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

    polled = await manager.poll_pending(session_id="session-b")
    assert polled is not None
    assert polled.request_id == second.request.request_id


@pytest.mark.asyncio
async def test_poll_pending_session_filter_timeout_returns_none(manager) -> None:
    await manager.evaluate(
        capability_id="run_command",
        params={"command": "echo session-a"},
        session_id="session-a",
        reason="Tool run_command requires approval",
    )

    polled = await manager.poll_pending(session_id="session-miss", timeout_seconds=0.05)
    assert polled is None


@pytest.mark.asyncio
async def test_poll_pending_session_filter_waiter_does_not_busy_loop_on_unrelated_pending(manager, monkeypatch) -> None:
    await manager.evaluate(
        capability_id="run_command",
        params={"command": "echo session-a"},
        session_id="session-a",
        reason="Tool run_command requires approval",
    )

    call_count = 0
    original = manager._oldest_pending_locked

    def tracked_oldest_pending(*, session_id: str | None = None):
        nonlocal call_count
        call_count += 1
        return original(session_id=session_id)

    monkeypatch.setattr(manager, "_oldest_pending_locked", tracked_oldest_pending)
    waiter = asyncio.create_task(manager.poll_pending(session_id="session-miss"))
    await asyncio.sleep(0.05)

    assert waiter.done() is False
    # A healthy waiter should sleep on condition changes instead of tight-loop polling.
    assert call_count < 30

    waiter.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await waiter


@pytest.mark.asyncio
async def test_poll_pending_waits_until_request_arrives(manager) -> None:
    waiter = asyncio.create_task(manager.poll_pending(timeout_seconds=1.0))
    await asyncio.sleep(0.05)

    first = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status --branch"},
        session_id="session-poll-wait",
        reason="Tool run_command requires approval",
    )
    assert first.request is not None

    polled = await waiter
    assert polled is not None
    assert polled.request_id == first.request.request_id


@pytest.mark.asyncio
async def test_poll_pending_timeout_returns_none(manager) -> None:
    polled = await manager.poll_pending(timeout_seconds=0.05)
    assert polled is None
