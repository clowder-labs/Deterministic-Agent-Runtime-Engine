from __future__ import annotations

import asyncio
import contextlib
import importlib
import json
import threading
import time

import pytest

from client.commands.approvals import handle_approvals_tokens
from client.commands.info import build_doctor_report
from client.commands.mcp import summarize_tools
from client.parser.command import Command, CommandType, parse_command
from client.parser.kv import parse_key_value_args
from client.runtime.action_client import ActionClientError, _parse_action_response
from client.runtime.task_runner import format_run_output
from dare_framework.config import Config


def test_parse_command_mode() -> None:
    parsed = parse_command("/mode plan")
    assert isinstance(parsed, Command)
    assert parsed.type == CommandType.MODE
    assert parsed.args == ["plan"]


def test_parse_command_plain_text() -> None:
    parsed = parse_command("build one file")
    assert isinstance(parsed, tuple)
    assert parsed[0] is None
    assert parsed[1] == "build one file"


def test_parse_command_single_slash_is_safe_plain_text() -> None:
    parsed = parse_command("/")
    assert isinstance(parsed, tuple)
    assert parsed[0] is None
    assert parsed[1] == "/"


def test_parse_key_value_args() -> None:
    positional, options = parse_key_value_args(["req-1", "scope=workspace", "matcher=exact_params"])
    assert positional == ["req-1"]
    assert options == {"scope": "workspace", "matcher": "exact_params"}


def test_format_run_output_variants() -> None:
    assert format_run_output("  ok  ") == "ok"
    assert format_run_output({"content": " done "}) == "done"
    assert format_run_output({"x": 1}) == "{'x': 1}"
    assert format_run_output(None) is None


def test_parse_action_response_error() -> None:
    with pytest.raises(ActionClientError) as excinfo:
        _parse_action_response(
            {
                "type": "error",
                "kind": "action",
                "target": "approvals:list",
                "code": "ACTION_HANDLER_FAILED",
                "reason": "failed",
            },
            expected_kind="action",
        )
    assert excinfo.value.code == "ACTION_HANDLER_FAILED"


def test_summarize_tools_split_mcp_and_local() -> None:
    class _Agent:
        @staticmethod
        def list_tool_defs():
            return [
                {"function": {"name": "read_file"}},
                {"function": {"name": "local_math:add"}},
            ]

    result = summarize_tools(_Agent())
    assert result["local_tools"] == ["read_file"]
    assert result["mcp_tools"] == ["local_math:add"]


@pytest.mark.asyncio
async def test_handle_approvals_tokens_grant() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    class _ActionClient:
        async def invoke_action(self, action, **params):  # noqa: ANN001
            action_id = action.value if hasattr(action, "value") else str(action)
            calls.append((action_id, {k: str(v) for k, v in params.items()}))
            return {"ok": True}

    payload = await handle_approvals_tokens(
        ["grant", "req-1", "scope=workspace", "matcher=exact_params"],
        action_client=_ActionClient(),  # type: ignore[arg-type]
    )
    assert payload == {"ok": True}
    assert calls == [
        (
            "approvals:grant",
            {
                "request_id": "req-1",
                "scope": "workspace",
                "matcher": "exact_params",
            },
        )
    ]


@pytest.mark.asyncio
async def test_handle_approvals_tokens_grant_with_session_id() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    class _ActionClient:
        async def invoke_action(self, action, **params):  # noqa: ANN001
            action_id = action.value if hasattr(action, "value") else str(action)
            calls.append((action_id, {k: str(v) for k, v in params.items()}))
            return {"ok": True}

    payload = await handle_approvals_tokens(
        ["grant", "req-1", "scope=workspace", "matcher=exact_params", "session_id=session-42"],
        action_client=_ActionClient(),  # type: ignore[arg-type]
    )
    assert payload == {"ok": True}
    assert calls == [
        (
            "approvals:grant",
            {
                "request_id": "req-1",
                "scope": "workspace",
                "matcher": "exact_params",
                "session_id": "session-42",
            },
        )
    ]


@pytest.mark.asyncio
async def test_main_approvals_grant_forwards_session_id(monkeypatch, tmp_path) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    config = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "llm": {
                "adapter": "openai",
                "model": "gpt-4o-mini",
                "api_key": "dummy",
            },
            "mcp_paths": [],
        }
    )

    captured_tokens: list[str] = []

    async def _fake_handle_approvals_tokens(tokens, *, action_client):  # noqa: ANN001
        captured_tokens[:] = tokens
        return {"ok": True}

    class _FakeRuntime:
        def __init__(self) -> None:
            self.client_channel = object()

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return _FakeRuntime()

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "handle_approvals_tokens", _fake_handle_approvals_tokens)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "approvals",
            "grant",
            "req-1",
            "--scope",
            "workspace",
            "--matcher",
            "exact_params",
            "--session-id",
            "session-42",
        ]
    )

    assert rc == 0
    assert captured_tokens == [
        "grant",
        "req-1",
        "scope=workspace",
        "matcher=exact_params",
        "session_id=session-42",
    ]


def test_build_doctor_report_warns_on_missing_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "llm": {
                "adapter": "openrouter",
                "model": "z-ai/glm-4.7",
            },
            "mcp_paths": ["./missing-mcp-path"],
        }
    )
    payload = build_doctor_report(config=config, model_probe_error="api key missing")
    assert payload["llm"]["adapter"] == "openrouter"
    assert payload["ok"] is False
    assert any("missing API key" in item for item in payload["warnings"])
    assert any("model adapter probe failed" in item for item in payload["warnings"])


def test_build_doctor_report_accepts_openai_with_key() -> None:
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "llm": {
                "adapter": "openai",
                "model": "gpt-4o-mini",
                "api_key": "dummy",
            },
            "mcp_paths": [],
        }
    )
    payload = build_doctor_report(config=config)
    assert payload["llm"]["api_key_present"] is True
    assert "workspace_dir" in payload


@pytest.mark.asyncio
async def test_main_doctor_does_not_bootstrap_runtime(monkeypatch, tmp_path) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    config = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "llm": {
                "adapter": "openrouter",
                "model": "z-ai/glm-4.7",
                "api_key": "dummy",
            },
        }
    )

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fail_bootstrap(_options):  # noqa: ANN001
        raise AssertionError("bootstrap_runtime should not be called for doctor")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fail_bootstrap)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "doctor",
        ]
    )
    assert rc == 0


@pytest.mark.asyncio
async def test_run_chat_script_returns_nonzero_on_failure(monkeypatch) -> None:
    client_main = importlib.import_module("client.main")

    class _FakeResult:
        success = False
        output = None
        errors = ["boom"]

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        return _FakeResult()

    monkeypatch.setattr(client_main, "run_task", _fake_run_task)

    class _FakeClientChannel:
        async def poll(self, timeout=None):  # noqa: ANN001
            await asyncio.sleep(0)
            return None

    class _FakeRuntime:
        agent = object()
        channel = object()
        model = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        client_channel = _FakeClientChannel()

    rc = await client_main._run_chat(
        runtime=_FakeRuntime(),
        action_client=object(),
        output=client_main.OutputFacade("json"),
        mode="execute",
        script_lines=["do one failing task"],
    )
    assert rc == 1


@pytest.mark.asyncio
async def test_run_chat_script_executes_tasks_sequentially(monkeypatch) -> None:
    client_main = importlib.import_module("client.main")
    calls: list[str] = []
    first_started = asyncio.Event()
    release_first = asyncio.Event()

    class _FakeResult:
        success = True
        output = "ok"
        errors = None

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, conversation_id, transport)
        calls.append(task_text)
        if len(calls) == 1:
            first_started.set()
            await release_first.wait()
        return _FakeResult()

    monkeypatch.setattr(client_main, "run_task", _fake_run_task)

    class _FakeClientChannel:
        async def poll(self, timeout=None):  # noqa: ANN001
            await asyncio.sleep(0)
            return None

    class _FakeRuntime:
        agent = object()
        channel = object()
        model = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        client_channel = _FakeClientChannel()

    task = asyncio.create_task(
        client_main._run_chat(
            runtime=_FakeRuntime(),
            action_client=object(),
            output=client_main.OutputFacade("json"),
            mode="execute",
            script_lines=["task one", "task two"],
        )
    )
    await asyncio.wait_for(first_started.wait(), timeout=1.0)
    await asyncio.sleep(0)
    release_first.set()
    rc = await task

    assert rc == 0
    assert calls == ["task one", "task two"]


@pytest.mark.asyncio
async def test_approve_keeps_pending_plan_when_background_execution_is_running() -> None:
    client_main = importlib.import_module("client.main")
    state = client_main.CLISessionState(mode=client_main.ExecutionMode.PLAN)
    state.status = client_main.SessionStatus.AWAITING_APPROVAL
    state.pending_plan = {"steps": []}
    state.pending_task_description = "do pending task"

    blocker = asyncio.Event()

    async def _running_task() -> None:
        await blocker.wait()

    state.active_execution_task = asyncio.create_task(_running_task())
    try:
        quit_requested = await client_main._handle_shell_command(
            Command(type=CommandType.APPROVE, args=[], raw_input="/approve"),
            state=state,
            runtime=object(),
            action_client=object(),
            output=client_main.OutputFacade("json"),
            background_execute=True,
        )
        assert quit_requested is False
        assert state.pending_plan == {"steps": []}
        assert state.pending_task_description == "do pending task"
    finally:
        if state.active_execution_task is not None:
            state.active_execution_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await state.active_execution_task


@pytest.mark.asyncio
async def test_main_run_plan_preview_failure_returns_one(monkeypatch, tmp_path) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    config = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "llm": {
                "adapter": "openai",
                "model": "gpt-4o-mini",
                "api_key": "dummy",
            },
        }
    )

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    class _FakeRuntime:
        def __init__(self) -> None:
            self.agent = object()
            self.channel = object()
            self.model = object()
            self.config = config
            self.client_channel = object()

        async def close(self) -> None:
            return None

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return _FakeRuntime()

    async def _fake_preview_plan(*, task_text, model, workspace_dir, user_dir):  # noqa: ANN001
        _ = (task_text, model, workspace_dir, user_dir)
        raise RuntimeError("plan adapter unavailable")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "preview_plan", _fake_preview_plan)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "run",
            "--task",
            "summarize readme",
            "--mode",
            "plan",
        ]
    )
    assert rc == 1


@pytest.mark.asyncio
async def test_main_load_effective_config_failure_returns_two(tmp_path, capsys) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    config_dir = workspace / ".dare"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text("{malformed json", encoding="utf-8")

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "doctor",
        ]
    )

    assert rc == 2
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["type"] == "log"
    assert payload["level"] == "error"
    assert "invalid config" in payload["message"]


@pytest.mark.asyncio
async def test_main_bootstrap_failure_returns_one(monkeypatch, tmp_path, capsys) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    config = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "llm": {
                "adapter": "openai",
                "model": "gpt-4o-mini",
                "api_key": "dummy",
            },
        }
    )

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        raise RuntimeError("adapter unavailable")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "run",
            "--task",
            "summarize readme",
        ]
    )

    assert rc == 1
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["type"] == "log"
    assert payload["level"] == "error"
    assert "runtime bootstrap failed" in payload["message"]


@pytest.mark.asyncio
async def test_main_invalid_workspace_path_returns_two(tmp_path, capsys) -> None:
    client_main = importlib.import_module("client.main")
    workspace_file = tmp_path / "workspace_file"
    workspace_file.write_text("occupied", encoding="utf-8")
    user_dir = tmp_path / "user"
    user_dir.mkdir(parents=True, exist_ok=True)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace_file),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "doctor",
        ]
    )

    assert rc == 2
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["type"] == "log"
    assert payload["level"] == "error"


@pytest.mark.asyncio
async def test_main_mcp_command_failure_returns_one(monkeypatch, tmp_path, capsys) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    config = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "llm": {
                "adapter": "openai",
                "model": "gpt-4o-mini",
                "api_key": "dummy",
            },
        }
    )

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    class _FakeRuntime:
        def __init__(self) -> None:
            self.agent = object()
            self.channel = object()
            self.model = object()
            self.config = config
            self.client_channel = object()

        async def close(self) -> None:
            return None

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return _FakeRuntime()

    async def _fake_handle_mcp_tokens(_tokens, *, runtime):  # noqa: ANN001
        _ = runtime
        raise RuntimeError("manager unavailable")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "handle_mcp_tokens", _fake_handle_mcp_tokens)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "mcp",
            "reload",
        ]
    )

    assert rc == 1
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["type"] == "log"
    assert payload["level"] == "info"
    assert "/mcp list|inspect [tool_name]|reload [paths...]|unload" in payload["message"]


@pytest.mark.asyncio
async def test_main_chat_script_missing_file_returns_two(monkeypatch, tmp_path, capsys) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    config = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "llm": {
                "adapter": "openai",
                "model": "gpt-4o-mini",
                "api_key": "dummy",
            },
        }
    )

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    class _FakeRuntime:
        def __init__(self) -> None:
            self.agent = object()
            self.channel = object()
            self.model = object()
            self.config = config
            self.client_channel = object()

        async def close(self) -> None:
            return None

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return _FakeRuntime()

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)

    missing_script = tmp_path / "missing.script.txt"
    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "chat",
            "--script",
            str(missing_script),
        ]
    )

    assert rc == 2
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["type"] == "log"
    assert payload["level"] == "error"


@pytest.mark.asyncio
async def test_run_chat_script_returns_nonzero_on_command_error(monkeypatch) -> None:
    client_main = importlib.import_module("client.main")

    async def _fake_handle_shell_command(*_args, **_kwargs):
        raise ActionClientError("ACTION_HANDLER_FAILED", "failed", "approvals:list")

    monkeypatch.setattr(client_main, "_handle_shell_command", _fake_handle_shell_command)

    class _FakeClientChannel:
        async def poll(self, timeout=None):  # noqa: ANN001
            await asyncio.sleep(0)
            return None

    class _FakeRuntime:
        agent = object()
        channel = object()
        model = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        client_channel = _FakeClientChannel()

    rc = await client_main._run_chat(
        runtime=_FakeRuntime(),
        action_client=object(),
        output=client_main.OutputFacade("json"),
        mode="execute",
        script_lines=["/status"],
    )
    assert rc == 1


@pytest.mark.asyncio
async def test_run_chat_script_plan_preview_failure_returns_nonzero(monkeypatch) -> None:
    client_main = importlib.import_module("client.main")

    async def _fake_preview_plan(*, task_text, model, workspace_dir, user_dir):  # noqa: ANN001
        _ = (task_text, model, workspace_dir, user_dir)
        raise RuntimeError("planner unavailable")

    monkeypatch.setattr(client_main, "preview_plan", _fake_preview_plan)

    class _FakeClientChannel:
        async def poll(self, timeout=None):  # noqa: ANN001
            await asyncio.sleep(0)
            return None

    class _FakeRuntime:
        agent = object()
        channel = object()
        model = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        client_channel = _FakeClientChannel()

    rc = await client_main._run_chat(
        runtime=_FakeRuntime(),
        action_client=object(),
        output=client_main.OutputFacade("json"),
        mode="plan",
        script_lines=["generate a plan"],
    )
    assert rc == 1


@pytest.mark.asyncio
async def test_run_chat_interactive_input_does_not_block_event_loop(monkeypatch) -> None:
    client_main = importlib.import_module("client.main")

    class _NoopPump:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    async def _fake_run_cli_loop(*_args, **_kwargs):
        return True

    def _slow_input(_prompt: str) -> str:
        time.sleep(0.25)
        return "/quit"

    monkeypatch.setattr(client_main, "EventPump", _NoopPump)
    monkeypatch.setattr(client_main, "_run_cli_loop", _fake_run_cli_loop)
    monkeypatch.setattr("builtins.input", _slow_input)

    class _FakeRuntime:
        client_channel = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        model = object()
        channel = object()
        agent = object()

    start = time.monotonic()
    tick_at: float | None = None

    async def _ticker() -> None:
        nonlocal tick_at
        await asyncio.sleep(0.05)
        tick_at = time.monotonic()

    ticker_task = asyncio.create_task(_ticker())
    rc = await client_main._run_chat(
        runtime=_FakeRuntime(),
        action_client=object(),
        output=client_main.OutputFacade("json"),
        mode="execute",
        script_lines=None,
    )
    await ticker_task

    assert rc == 0
    assert tick_at is not None
    assert tick_at - start < 0.2


@pytest.mark.asyncio
async def test_run_chat_interactive_waits_for_completion_before_reprompt(monkeypatch) -> None:
    client_main = importlib.import_module("client.main")
    task_finished = threading.Event()

    class _NoopPump:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    class _FakeResult:
        success = True
        output = "done"
        errors = None

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.05)
        task_finished.set()
        return _FakeResult()

    input_calls = 0

    def _input(_prompt: str) -> str:
        nonlocal input_calls
        input_calls += 1
        if input_calls == 1:
            return "do work"
        assert task_finished.is_set(), "prompt returned before task finished"
        return "/quit"

    monkeypatch.setattr(client_main, "EventPump", _NoopPump)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)
    monkeypatch.setattr("builtins.input", _input)

    class _FakeRuntime:
        client_channel = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        model = object()
        channel = object()
        agent = object()

    rc = await client_main._run_chat(
        runtime=_FakeRuntime(),
        action_client=object(),
        output=client_main.OutputFacade("json"),
        mode="execute",
        script_lines=None,
    )

    assert rc == 0
    assert input_calls == 2


@pytest.mark.asyncio
async def test_run_chat_interactive_json_mode_reprompts_when_approval_is_pending(monkeypatch) -> None:
    client_main = importlib.import_module("client.main")
    approval_emitted = threading.Event()
    task_released = asyncio.Event()
    task_finished = threading.Event()

    class _ApprovalPump:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            self._on_event = kwargs["on_event"]
            self._task: asyncio.Task[None] | None = None

        def start(self) -> None:
            self._task = asyncio.create_task(self._emit())

        async def stop(self) -> None:
            if self._task is None:
                return
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        async def _emit(self) -> None:
            await asyncio.sleep(0.05)
            approval_emitted.set()
            maybe_awaitable = self._on_event(
                {
                    "type": "approval_pending",
                    "resp": {
                        "request": {"request_id": "req-1"},
                        "capability_id": "run_command",
                        "tool_name": "run_command",
                    },
                }
            )
            if maybe_awaitable is not None:
                await maybe_awaitable

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await task_released.wait()
        task_finished.set()
        return type("OkResult", (), {"success": True, "output": "done", "errors": None})()

    input_calls = 0

    def _input(_prompt: str) -> str:
        nonlocal input_calls
        input_calls += 1
        if input_calls == 1:
            return "do work"
        assert approval_emitted.is_set(), "prompt returned before approval pending surfaced"
        assert task_finished.is_set() is False, "prompt should return while task is still waiting for approval"
        task_released.set()
        return "/quit"

    monkeypatch.setattr(client_main, "EventPump", _ApprovalPump)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)
    monkeypatch.setattr("builtins.input", _input)

    class _FakeRuntime:
        client_channel = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        model = object()
        channel = object()
        agent = object()

    rc = await client_main._run_chat(
        runtime=_FakeRuntime(),
        action_client=object(),
        output=client_main.OutputFacade("json"),
        mode="execute",
        script_lines=None,
    )

    assert rc == 0
    assert input_calls == 2


@pytest.mark.asyncio
async def test_run_chat_interactive_human_mode_prompts_rich_inline_approval_and_grants(monkeypatch, capsys) -> None:
    client_main = importlib.import_module("client.main")
    approval_emitted = threading.Event()
    task_released = asyncio.Event()
    task_finished = threading.Event()
    action_calls: list[tuple[str, dict[str, str]]] = []

    class _ApprovalPump:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            self._on_event = kwargs["on_event"]
            self._task: asyncio.Task[None] | None = None

        def start(self) -> None:
            self._task = asyncio.create_task(self._emit())

        async def stop(self) -> None:
            if self._task is None:
                return
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        async def _emit(self) -> None:
            await asyncio.sleep(0.05)
            approval_emitted.set()
            maybe_awaitable = self._on_event(
                {
                    "type": "approval_pending",
                    "resp": {
                        "request": {
                            "request_id": "req-1",
                            "reason": "Tool run_command requires approval",
                            "command": "git status",
                            "params": {"command": "git status", "cwd": "/tmp/workspace"},
                        },
                        "capability_id": "run_command",
                        "tool_name": "run_command",
                    },
                }
            )
            if maybe_awaitable is not None:
                await maybe_awaitable

    class _ActionClient:
        async def invoke_action(self, action, **params):  # noqa: ANN001
            action_id = action.value if hasattr(action, "value") else str(action)
            action_calls.append((action_id, {key: str(value) for key, value in params.items()}))
            task_released.set()
            return {"ok": True}

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await task_released.wait()
        task_finished.set()
        return type("OkResult", (), {"success": True, "output": "done", "errors": None})()

    prompts: list[str] = []

    def _input(prompt: str) -> str:
        prompts.append(prompt)
        if len(prompts) == 1:
            assert prompt == "dare> "
            return "do work"
        if len(prompts) == 2:
            assert approval_emitted.wait(timeout=1), "approval prompt rendered before pending event"
            assert prompt == "approve> "
            assert task_finished.is_set() is False, "task should still be waiting during approval prompt"
            return "y"
        assert task_finished.is_set(), "chat prompt returned before approved task completed"
        assert prompt == "dare> "
        return "/quit"

    monkeypatch.setattr(client_main, "EventPump", _ApprovalPump)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)
    monkeypatch.setattr("builtins.input", _input)

    class _FakeRuntime:
        client_channel = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        model = object()
        channel = object()
        agent = object()

    rc = await client_main._run_chat(
        runtime=_FakeRuntime(),
        action_client=_ActionClient(),
        output=client_main.OutputFacade("human"),
        mode="execute",
        script_lines=None,
    )

    assert rc == 0
    assert prompts == ["dare> ", "approve> ", "dare> "]
    assert action_calls == [
        (
            "approvals:grant",
            {
                "request_id": "req-1",
                "scope": "once",
                "matcher": "exact_params",
            },
        )
    ]
    output = capsys.readouterr().out
    assert "Agent wants to run a shell command." in output
    assert "Reason: Tool run_command requires approval" in output
    assert "Command: git status" in output
    assert "Cwd: /tmp/workspace" in output
    assert "1. Allow once" in output
    assert "2. Always allow this exact command in this session" in output
    assert "3. Deny (default)" in output


@pytest.mark.asyncio
async def test_run_chat_interactive_human_mode_prompts_inline_approval_and_denies(monkeypatch) -> None:
    client_main = importlib.import_module("client.main")
    approval_emitted = threading.Event()
    task_released = asyncio.Event()
    task_finished = threading.Event()
    action_calls: list[tuple[str, dict[str, str]]] = []

    class _ApprovalPump:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            self._on_event = kwargs["on_event"]
            self._task: asyncio.Task[None] | None = None

        def start(self) -> None:
            self._task = asyncio.create_task(self._emit())

        async def stop(self) -> None:
            if self._task is None:
                return
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        async def _emit(self) -> None:
            await asyncio.sleep(0.05)
            approval_emitted.set()
            maybe_awaitable = self._on_event(
                {
                    "type": "approval_pending",
                    "resp": {
                        "request": {
                            "request_id": "req-1",
                            "reason": "Tool run_command requires approval",
                            "command": "git status",
                            "params": {"command": "git status", "cwd": "/tmp/workspace"},
                        },
                        "capability_id": "run_command",
                        "tool_name": "run_command",
                    },
                }
            )
            if maybe_awaitable is not None:
                await maybe_awaitable

    class _ActionClient:
        async def invoke_action(self, action, **params):  # noqa: ANN001
            action_id = action.value if hasattr(action, "value") else str(action)
            action_calls.append((action_id, {key: str(value) for key, value in params.items()}))
            task_released.set()
            return {"ok": True}

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await task_released.wait()
        task_finished.set()
        return type(
            "DeniedResult",
            (),
            {"success": False, "output": None, "errors": ["tool invocation denied by human approval"]},
        )()

    prompts: list[str] = []

    def _input(prompt: str) -> str:
        prompts.append(prompt)
        if len(prompts) == 1:
            assert prompt == "dare> "
            return "do work"
        if len(prompts) == 2:
            assert approval_emitted.wait(timeout=1), "approval prompt rendered before pending event"
            assert prompt == "approve> "
            assert task_finished.is_set() is False, "task should still be waiting during approval prompt"
            return "n"
        assert task_finished.is_set(), "chat prompt returned before denied task completed"
        assert prompt == "dare> "
        return "/quit"

    monkeypatch.setattr(client_main, "EventPump", _ApprovalPump)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)
    monkeypatch.setattr("builtins.input", _input)

    class _FakeRuntime:
        client_channel = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        model = object()
        channel = object()
        agent = object()

    rc = await client_main._run_chat(
        runtime=_FakeRuntime(),
        action_client=_ActionClient(),
        output=client_main.OutputFacade("human"),
        mode="execute",
        script_lines=None,
    )

    assert rc == 0
    assert prompts == ["dare> ", "approve> ", "dare> "]
    assert action_calls == [
        (
            "approvals:deny",
            {
                "request_id": "req-1",
                "scope": "once",
                "matcher": "exact_params",
            },
        )
    ]


@pytest.mark.asyncio
async def test_run_chat_interactive_human_mode_can_remember_same_command_for_session(monkeypatch, capsys) -> None:
    client_main = importlib.import_module("client.main")
    approval_emitted = threading.Event()
    task_released = asyncio.Event()
    task_finished = threading.Event()
    action_calls: list[tuple[str, dict[str, str]]] = []

    class _ApprovalPump:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            self._on_event = kwargs["on_event"]
            self._task: asyncio.Task[None] | None = None

        def start(self) -> None:
            self._task = asyncio.create_task(self._emit())

        async def stop(self) -> None:
            if self._task is None:
                return
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        async def _emit(self) -> None:
            await asyncio.sleep(0.05)
            approval_emitted.set()
            maybe_awaitable = self._on_event(
                {
                    "type": "approval_pending",
                    "resp": {
                        "request": {
                            "request_id": "req-1",
                            "reason": "Tool run_command requires approval",
                            "command": "git status",
                            "params": {"command": "git status", "cwd": "/tmp/workspace"},
                        },
                        "capability_id": "run_command",
                        "tool_name": "run_command",
                    },
                }
            )
            if maybe_awaitable is not None:
                await maybe_awaitable

    class _ActionClient:
        async def invoke_action(self, action, **params):  # noqa: ANN001
            action_id = action.value if hasattr(action, "value") else str(action)
            action_calls.append((action_id, {key: str(value) for key, value in params.items()}))
            task_released.set()
            return {"ok": True}

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await task_released.wait()
        task_finished.set()
        return type("OkResult", (), {"success": True, "output": "done", "errors": None})()

    prompts: list[str] = []

    def _input(prompt: str) -> str:
        prompts.append(prompt)
        if len(prompts) == 1:
            assert prompt == "dare> "
            return "do work"
        if len(prompts) == 2:
            assert approval_emitted.wait(timeout=1), "approval prompt rendered before pending event"
            assert prompt == "approve> "
            assert task_finished.is_set() is False, "task should still be waiting during approval prompt"
            return "2"
        assert task_finished.is_set(), "chat prompt returned before approved task completed"
        assert prompt == "dare> "
        return "/quit"

    monkeypatch.setattr(client_main, "EventPump", _ApprovalPump)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)
    monkeypatch.setattr("builtins.input", _input)

    class _FakeRuntime:
        client_channel = object()
        config = Config.from_dict({"workspace_dir": ".", "user_dir": "."})
        model = object()
        channel = object()
        agent = object()

    rc = await client_main._run_chat(
        runtime=_FakeRuntime(),
        action_client=_ActionClient(),
        output=client_main.OutputFacade("human"),
        mode="execute",
        script_lines=None,
    )

    assert rc == 0
    assert prompts == ["dare> ", "approve> ", "dare> "]
    assert action_calls == [
        (
            "approvals:grant",
            {
                "request_id": "req-1",
                "scope": "session",
                "matcher": "exact_params",
            },
        )
    ]
    output = capsys.readouterr().out
    assert "Same command will be auto-approved for the rest of this session." in output


@pytest.mark.asyncio
async def test_main_script_command_missing_file_returns_two(monkeypatch, tmp_path, capsys) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    config = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "llm": {
                "adapter": "openai",
                "model": "gpt-4o-mini",
                "api_key": "dummy",
            },
        }
    )

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    class _FakeRuntime:
        def __init__(self) -> None:
            self.agent = object()
            self.channel = object()
            self.model = object()
            self.config = config
            self.client_channel = object()

        async def close(self) -> None:
            return None

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return _FakeRuntime()

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)

    missing_script = tmp_path / "missing.script.txt"
    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "script",
            "--file",
            str(missing_script),
        ]
    )

    assert rc == 2
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["type"] == "log"
    assert payload["level"] == "error"


def test_output_facade_json_schema(capsys) -> None:
    client_main = importlib.import_module("client.main")
    output = client_main.OutputFacade("json")
    output.info("hello")
    output.emit_data({"ok": True})
    output.emit_event("transport", {"x": 1})

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    third = json.loads(lines[2])

    assert first == {"type": "log", "level": "info", "message": "hello"}
    assert second == {"type": "result", "data": {"ok": True}}
    assert third == {"type": "event", "event": "transport", "data": {"x": 1}}


def test_output_facade_headless_schema(capsys) -> None:
    client_main = importlib.import_module("client.main")
    output = client_main.OutputFacade("headless")
    output.set_protocol_context(session_id="session-1", run_id="run-1")
    output.emit_event("task.started", {"task": "demo"})

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])

    assert payload["schema_version"] == "client-headless-event-envelope.v1"
    assert payload["session_id"] == "session-1"
    assert payload["run_id"] == "run-1"
    assert payload["seq"] == 1
    assert payload["event"] == "task.started"
    assert payload["data"] == {"task": "demo"}
    assert "ts" in payload


@pytest.mark.asyncio
async def test_on_transport_event_headless_maps_tool_hook_events(capsys) -> None:
    client_main = importlib.import_module("client.main")
    output = client_main.OutputFacade("headless")
    output.set_protocol_context(session_id="session-1", run_id="run-1")

    await client_main._on_transport_event_async(
        {
            "type": "hook",
            "phase": "before_tool",
            "payload": {
                "tool_name": "read_file",
                "tool_call_id": "call-1",
                "capability_id": "read_file",
            },
        },
        output=output,
    )
    await client_main._on_transport_event_async(
        {
            "type": "hook",
            "phase": "after_tool",
            "payload": {
                "tool_name": "read_file",
                "tool_call_id": "call-1",
                "capability_id": "read_file",
                "success": True,
            },
        },
        output=output,
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert [line["event"] for line in lines] == ["tool.invoke", "tool.result"]
    assert lines[0]["data"]["tool_name"] == "read_file"
    assert lines[1]["data"]["success"] is True


def test_sync_main_wraps_async_main(monkeypatch: pytest.MonkeyPatch) -> None:
    client_main = importlib.import_module("client.main")

    async def _fake_main(argv=None):  # noqa: ANN001
        _ = argv
        return 7

    monkeypatch.setattr(client_main, "main", _fake_main)
    rc = client_main.sync_main(["doctor"])
    assert rc == 7


def test_default_auto_approve_tools_are_runtime_tool_subset() -> None:
    client_main = importlib.import_module("client.main")
    runtime_bootstrap = importlib.import_module("client.runtime.bootstrap")

    runtime_tool_names = {
        runtime_bootstrap.ReadFileTool().name,
        runtime_bootstrap.WriteFileTool().name,
        runtime_bootstrap.SearchCodeTool().name,
        runtime_bootstrap.RunCommandTool().name,
    }

    assert client_main.DEFAULT_AUTO_APPROVE_TOOLS.issubset(runtime_tool_names)


def test_default_auto_approve_tools_exclude_write_file() -> None:
    client_main = importlib.import_module("client.main")
    runtime_bootstrap = importlib.import_module("client.runtime.bootstrap")

    assert runtime_bootstrap.WriteFileTool().name not in client_main.DEFAULT_AUTO_APPROVE_TOOLS


def test_cli_raises_system_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    client_main = importlib.import_module("client.main")
    monkeypatch.setattr(client_main, "sync_main", lambda argv=None: 5)
    with pytest.raises(SystemExit) as excinfo:
        client_main.cli()
    assert excinfo.value.code == 5


def test_chat_parser_rejects_headless_flag() -> None:
    client_main = importlib.import_module("client.main")
    parser = client_main._build_parser()

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["chat", "--headless"])

    assert excinfo.value.code == 2


@pytest.mark.asyncio
async def test_main_run_headless_rejects_legacy_output(monkeypatch, tmp_path, capsys) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)

    config = Config.from_dict(
        {
            "workspace_dir": str(workspace),
            "user_dir": str(user_dir),
            "llm": {
                "adapter": "openai",
                "model": "gpt-4o-mini",
                "api_key": "dummy",
            },
        }
    )

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        raise AssertionError("bootstrap_runtime should not run for invalid headless args")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "run",
            "--task",
            "summarize readme",
            "--headless",
        ]
    )

    assert rc == 2
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["schema_version"] == "client-headless-event-envelope.v1"
    assert payload["event"] == "log.error"
    assert "cannot combine --headless with legacy --output" in payload["data"]["message"]
