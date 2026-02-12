from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
import sys

import pytest

from dare_framework.tool._internal.control.approval_manager import (
    ApprovalDecision,
    ApprovalEvaluationStatus,
    JsonApprovalRuleStore,
    ToolApprovalManager,
)


def _resolve_example_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = (
        "05-dare-coding-agent-enhanced",
        "04-dare-coding-agent",
        "03-dare-coding-agent",
    )
    for candidate in candidates:
        path = root / "examples" / candidate
        if (path / "cli.py").exists():
            return path
    raise FileNotFoundError("Unable to locate examples/*/cli.py for coding-agent example tests.")


EXAMPLE_DIR = _resolve_example_dir()
sys.path.insert(0, str(EXAMPLE_DIR))

import cli  # type: ignore  # noqa: E402


def test_parse_command_mode_plan() -> None:
    command = cli.parse_command("/mode plan")
    assert isinstance(command, cli.Command)
    assert command.type == cli.CommandType.MODE
    assert command.args == ["plan"]


def test_parse_command_quit() -> None:
    command = cli.parse_command("/quit")
    assert isinstance(command, cli.Command)
    assert command.type == cli.CommandType.QUIT


def test_parse_command_task_text() -> None:
    command = cli.parse_command("build a demo")
    assert isinstance(command, tuple)
    assert command[0] is None
    assert command[1] == "build a demo"


def test_parse_command_approvals() -> None:
    command = cli.parse_command("/approvals list")
    assert isinstance(command, cli.Command)
    assert command.type == cli.CommandType.APPROVALS
    assert command.args == ["list"]


def test_load_script_lines(tmp_path: Path) -> None:
    script = tmp_path / "demo.txt"
    script.write_text("""
# comment
/mode plan

Create a file
/approve
""", encoding="utf-8")

    lines = cli.load_script_lines(script)
    assert lines == ["/mode plan", "Create a file", "/approve"]


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
async def test_handle_approvals_command_list_and_grant(tmp_path: Path) -> None:
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

    await cli._handle_approvals_command(  # type: ignore[attr-defined]
        ["list"],
        agent=_FakeAgent(),
        display=display,
    )
    assert any("pending" in msg for level, msg in display.messages if level == "info")

    wait_task = asyncio.create_task(manager.wait_for_resolution(request_id))
    await cli._handle_approvals_command(  # type: ignore[attr-defined]
        ["grant", request_id, "scope=workspace", "matcher=exact_params"],
        agent=_FakeAgent(),
        display=display,
    )
    assert await wait_task == ApprovalDecision.ALLOW


@pytest.mark.asyncio
async def test_run_cli_loop_background_execute_allows_followup_commands(monkeypatch) -> None:
    started = asyncio.Event()
    finished = asyncio.Event()

    async def _fake_run_task(_agent, _task_text: str, _display) -> None:
        started.set()
        await finished.wait()

    monkeypatch.setattr(cli, "run_task", _fake_run_task)

    class _FakeAgent:
        _approval_manager = None

    state = cli.CLISessionState(mode=cli.ExecutionMode.EXECUTE)
    display = _CaptureDisplay()

    state, _quit = await cli.run_cli_loop(
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
    assert state.status == cli.SessionStatus.RUNNING

    await cli.run_cli_loop(
        ["/status"],
        agent=_FakeAgent(),
        model=object(),
        display=display,
        state=state,
        background_execute=True,
    )
    assert any("running=True" in msg for level, msg in display.messages if level == "info")

    finished.set()
    with contextlib.suppress(asyncio.CancelledError):
        await state.active_execution_task
