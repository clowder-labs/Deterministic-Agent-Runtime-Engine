from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys

import pytest

from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalEvaluationStatus,
    JsonApprovalRuleStore,
    ToolApprovalManager,
)


def _load_cli_module(module_name: str, relative_cli_path: str):
    root = Path(__file__).resolve().parents[2]
    cli_path = root / relative_cli_path
    example_dir = cli_path.parent
    if str(example_dir) not in sys.path:
        sys.path.insert(0, str(example_dir))
    spec = importlib.util.spec_from_file_location(module_name, cli_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {cli_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_command_approvals_mcp_cli() -> None:
    cli_mcp = _load_cli_module(
        "examples_06_cli",
        "examples/06-dare-coding-agent-mcp/cli.py",
    )
    command = cli_mcp.parse_command("/approvals list")
    assert isinstance(command, cli_mcp.Command)
    assert command.type == cli_mcp.CommandType.APPROVALS
    assert command.args == ["list"]


class _CaptureDisplay:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def info(self, text: str) -> None:
        self.messages.append(("info", text))

    def warn(self, text: str) -> None:
        self.messages.append(("warn", text))

    def ok(self, text: str) -> None:
        self.messages.append(("ok", text))

    def error(self, text: str) -> None:
        self.messages.append(("error", text))

    def header(self, _title: str) -> None:
        return

    def show_mode(self, _mode) -> None:
        return


@pytest.mark.asyncio
async def test_handle_approvals_command_list_and_grant_mcp_cli(tmp_path: Path) -> None:
    cli_mcp = _load_cli_module(
        "examples_06_cli_handle",
        "examples/06-dare-coding-agent-mcp/cli.py",
    )
    manager = ToolApprovalManager(
        workspace_store=JsonApprovalRuleStore(tmp_path / "workspace" / "approvals.json"),
        user_store=JsonApprovalRuleStore(tmp_path / "user" / "approvals.json"),
    )
    evaluation = await manager.evaluate(
        capability_id="run_command",
        params={"command": "git status --short"},
        session_id="session-test",
        reason="Tool run_command requires approval",
    )
    assert evaluation.status == ApprovalEvaluationStatus.PENDING
    assert evaluation.request is not None
    request_id = evaluation.request.request_id

    class _FakeAgent:
        _approval_manager = manager

    display = _CaptureDisplay()
    await cli_mcp._handle_approvals_command(  # type: ignore[attr-defined]
        ["list"],
        agent=_FakeAgent(),
        display=display,
    )
    assert any("pending" in msg for level, msg in display.messages if level == "info")

    wait_task = asyncio.create_task(manager.wait_for_resolution(request_id))
    await cli_mcp._handle_approvals_command(  # type: ignore[attr-defined]
        ["grant", request_id, "scope=workspace", "matcher=exact_params"],
        agent=_FakeAgent(),
        display=display,
    )
    assert await wait_task == ApprovalDecision.ALLOW


@pytest.mark.asyncio
async def test_run_cli_loop_background_execute_allows_followup_commands_mcp_cli(monkeypatch) -> None:
    cli_mcp = _load_cli_module(
        "examples_06_cli_background",
        "examples/06-dare-coding-agent-mcp/cli.py",
    )
    started = asyncio.Event()
    finished = asyncio.Event()

    async def _fake_run_task(_agent, _task_text: str, _display) -> None:
        started.set()
        await finished.wait()

    monkeypatch.setattr(cli_mcp, "run_task", _fake_run_task)

    class _FakeAgent:
        _approval_manager = None

    state = cli_mcp.CLISessionState(mode=cli_mcp.ExecutionMode.EXECUTE)
    display = _CaptureDisplay()

    state, _quit = await cli_mcp.run_cli_loop(
        ["build one thing"],
        agent=_FakeAgent(),
        model=object(),
        display=display,
        state=state,
        background_execute=True,
    )
    await asyncio.wait_for(started.wait(), timeout=1.0)
    assert state.active_execution_task is not None
    assert not state.active_execution_task.done()
    assert state.status == cli_mcp.SessionStatus.RUNNING

    await cli_mcp.run_cli_loop(
        ["/status"],
        agent=_FakeAgent(),
        model=object(),
        display=display,
        state=state,
        background_execute=True,
    )
    assert any("running=True" in msg for level, msg in display.messages if level == "info")

    finished.set()
    await state.active_execution_task
