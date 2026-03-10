from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_example_module(module_name: str, relative_path: str):
    root = Path(__file__).resolve().parents[2]
    module_path = root / relative_path
    example_dir = module_path.parent
    if str(example_dir) not in sys.path:
        sys.path.insert(0, str(example_dir))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_examples_04_cli_default_workspace_is_cwd() -> None:
    module = _load_example_module(
        "examples_04_cli_workspace_default",
        "examples/04-dare-coding-agent/cli.py",
    )
    parser = module._build_parser()
    args = parser.parse_args([])
    assert args.workspace == str(Path.cwd())


def test_examples_04_cli_parser_accepts_conversation_id() -> None:
    module = _load_example_module(
        "examples_04_cli_parser_conversation_id",
        "examples/04-dare-coding-agent/cli.py",
    )
    parser = module._build_parser()
    args = parser.parse_args(["--conversation-id", "session-fixed"])
    assert args.conversation_id == "session-fixed"


def test_examples_04_cli_parse_approvals_command() -> None:
    module = _load_example_module(
        "examples_04_cli_parse_approvals",
        "examples/04-dare-coding-agent/cli.py",
    )
    command = module.parse_command("/approvals list")
    assert isinstance(command, module.Command)
    assert command.type == module.CommandType.APPROVALS
    assert command.args == ["list"]


@pytest.mark.asyncio
async def test_examples_04_cli_streaming_event_log_requests_approval() -> None:
    module = _load_example_module(
        "examples_04_cli_approval_prompt",
        "examples/04-dare-coding-agent/cli.py",
    )

    class _FakeApprovalManager:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str]] = []

        async def grant(self, request_id: str, *, scope, matcher, matcher_value=None):  # noqa: ANN001
            _ = matcher_value
            self.calls.append(("grant", request_id, f"{scope.value}:{matcher.value}"))
            return None

        async def deny(self, request_id: str, *, scope, matcher, matcher_value=None):  # noqa: ANN001
            _ = matcher_value
            self.calls.append(("deny", request_id, f"{scope.value}:{matcher.value}"))
            return None

    approval_manager = _FakeApprovalManager()
    emitted: list[tuple[str, dict]] = []

    event_log = module.StreamingEventLog(
        lambda event_type, payload: emitted.append((event_type, payload)),
        approval_manager=approval_manager,
        prompt_fn=lambda _prompt: "y",
    )

    await event_log.append(
        "exec.waiting_human",
        {
            "checkpoint_id": "req-1",
            "reason": "Tool run_command requires approval",
        },
    )

    assert approval_manager.calls == [("grant", "req-1", "once:exact_params")]


@pytest.mark.asyncio
async def test_examples_04_cli_handle_approvals_list_and_grant(tmp_path: Path, capsys) -> None:
    module = _load_example_module(
        "examples_04_cli_handle_approvals",
        "examples/04-dare-coding-agent/cli.py",
    )
    manager = module.ToolApprovalManager.from_paths(
        workspace_dir=tmp_path / "workspace",
        user_dir=tmp_path / "user",
    )
    evaluation = await manager.evaluate(
        capability_id="run_command",
        params={"command": "date"},
        session_id="session-1",
        reason="Tool run_command requires approval",
    )
    request_id = evaluation.request.request_id

    class _Agent:
        _approval_manager = manager

    display = module.CLIDisplay()
    await module._handle_approvals_command(["list"], agent=_Agent(), display=display)
    list_output = capsys.readouterr().out
    assert "pending=1" in list_output

    await module._handle_approvals_command(
        ["grant", request_id, "scope=workspace", "matcher=exact_params"],
        agent=_Agent(),
        display=display,
    )
    grant_output = capsys.readouterr().out
    assert f"grant applied: {request_id}" in grant_output


@pytest.mark.asyncio
async def test_examples_04_cli_run_task_includes_conversation_metadata() -> None:
    module = _load_example_module(
        "examples_04_cli_run_task_conversation",
        "examples/04-dare-coding-agent/cli.py",
    )
    captured_task = {}

    class _Agent:
        async def __call__(self, task):
            captured_task["task"] = task

            class _Result:
                success = True
                output = "ok"
                errors = []

            return _Result()

    display = module.CLIDisplay()
    await module.run_task(
        _Agent(),
        "hello",
        display,
        conversation_id="session-42",
    )
    task = captured_task["task"]
    assert isinstance(task, module.Message)
    assert task.text == "hello"
    assert task.metadata.get("conversation_id") == "session-42"


@pytest.mark.asyncio
async def test_examples_04_cli_run_cli_loop_passes_state_conversation_id(monkeypatch) -> None:
    module = _load_example_module(
        "examples_04_cli_run_cli_loop_conversation",
        "examples/04-dare-coding-agent/cli.py",
    )
    captured_ids: list[str | None] = []

    async def _fake_run_task(_agent, _task_text: str, _display, *, conversation_id=None):  # noqa: ANN001
        captured_ids.append(conversation_id)
        return None

    monkeypatch.setattr(module, "run_task", _fake_run_task)
    state = module.CLISessionState(conversation_id="session-fixed")

    await module.run_cli_loop(
        ["hello"],
        agent=object(),
        model=object(),
        display=module.CLIDisplay(),
        state=state,
    )

    assert captured_ids == ["session-fixed"]
