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
from client.runtime.action_client import ActionClientError, TransportActionClient, _parse_action_response
from client.runtime.task_runner import format_run_output
from dare_framework.config import Config
from dare_framework.context import Message
from dare_framework.transport import ActionPayload, ControlPayload, EnvelopeKind, TransportEnvelope


def test_parse_command_mode() -> None:
    parsed = parse_command("/mode plan")
    assert isinstance(parsed, Command)
    assert parsed.type == CommandType.MODE
    assert parsed.args == ["plan"]


def test_parse_command_sessions() -> None:
    parsed = parse_command("/sessions list")
    assert isinstance(parsed, Command)
    assert parsed.type == CommandType.SESSIONS
    assert parsed.args == ["list"]


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
            ActionPayload(
                id="action-error-1",
                resource_action="approvals:list",
                ok=False,
                code="ACTION_HANDLER_FAILED",
                reason="failed",
            ),
            expected_kind="action",
        )
    assert excinfo.value.code == "ACTION_HANDLER_FAILED"


def test_parse_action_response_accepts_typed_action_payload() -> None:
    payload = ActionPayload(
        id="action-reply-1",
        resource_action="tools:list",
        ok=True,
        result={"items": ["read_file"]},
    )

    assert _parse_action_response(payload, expected_kind="action") == {"items": ["read_file"]}


def test_parse_action_response_accepts_typed_control_payload() -> None:
    payload = ControlPayload(
        id="control-reply-1",
        control_id="interrupt",
        ok=True,
        result={"accepted": True},
    )

    assert _parse_action_response(payload, expected_kind="control") == {"accepted": True}


def test_parse_action_response_rejects_legacy_dict_contract() -> None:
    with pytest.raises(ActionClientError, match="INVALID_RESPONSE"):
        _parse_action_response(
            {
                "type": "result",
                "kind": "action",
                "target": "approvals:list",
                "resp": {"result": {"pending": []}},
            },
            expected_kind="action",
        )


@pytest.mark.asyncio
async def test_transport_action_client_sends_typed_action_and_control_payloads() -> None:
    sent: list[TransportEnvelope] = []

    class _Channel:
        async def ask(self, envelope: TransportEnvelope, *, timeout: float | None = None):  # noqa: ANN001
            _ = timeout
            sent.append(envelope)
            if envelope.kind == EnvelopeKind.ACTION:
                return TransportEnvelope(
                    id="reply-action",
                    kind=EnvelopeKind.ACTION,
                    payload=ActionPayload(
                        id="reply-action-payload",
                        resource_action="tools:list",
                        ok=True,
                        result={"items": []},
                    ),
                )
            return TransportEnvelope(
                id="reply-control",
                kind=EnvelopeKind.CONTROL,
                payload=ControlPayload(
                    id="reply-control-payload",
                    control_id="interrupt",
                    ok=True,
                    result={"accepted": True},
                ),
            )

    client = TransportActionClient(_Channel())  # type: ignore[arg-type]

    action_result = await client.invoke_action("tools:list", scope="workspace")
    control_result = await client.invoke_control("interrupt")

    assert action_result == {"items": []}
    assert control_result == {"accepted": True}
    assert isinstance(sent[0].payload, ActionPayload)
    assert sent[0].payload.resource_action == "tools:list"
    assert sent[0].payload.params == {"scope": "workspace"}
    assert isinstance(sent[1].payload, ControlPayload)
    assert sent[1].payload.control_id == "interrupt"


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


def test_build_doctor_report_accepts_anthropic_with_key() -> None:
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "llm": {
                "adapter": "anthropic",
                "model": "claude-sonnet-4-5",
                "api_key": "dummy",
            },
            "mcp_paths": [],
        }
    )
    payload = build_doctor_report(config=config)
    assert payload["llm"]["adapter"] == "anthropic"
    assert payload["llm"]["api_key_present"] is True
    assert not any("unsupported adapter configured" in item for item in payload["warnings"])


def test_build_doctor_report_accepts_huawei_modelarts_with_key() -> None:
    config = Config.from_dict(
        {
            "workspace_dir": ".",
            "user_dir": ".",
            "llm": {
                "adapter": "huawei-modelarts",
                "model": "modelarts-pro",
                "api_key": "dummy",
            },
            "mcp_paths": [],
        }
    )
    payload = build_doctor_report(config=config)
    assert payload["llm"]["adapter"] == "huawei-modelarts"
    assert payload["llm"]["api_key_present"] is True
    assert not any("unsupported adapter configured" in item for item in payload["warnings"])


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
                    "id": "req-1",
                    "select_kind": "ask",
                    "select_domain": "approval",
                    "metadata": {
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
                    "id": "req-1",
                    "select_kind": "ask",
                    "select_domain": "approval",
                    "metadata": {
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
                    "id": "req-1",
                    "select_kind": "ask",
                    "select_domain": "approval",
                    "metadata": {
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
                    "id": "req-1",
                    "select_kind": "ask",
                    "select_domain": "approval",
                    "metadata": {
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
            "message_kind": "summary",
            "text": "hook:before_tool",
            "data": {
                "source": "hook",
                "phase": "before_tool",
                "payload": {
                    "tool_name": "read_file",
                    "tool_call_id": "call-1",
                    "capability_id": "read_file",
                },
            },
        },
        output=output,
    )
    await client_main._on_transport_event_async(
        {
            "message_kind": "summary",
            "text": "hook:after_tool",
            "data": {
                "source": "hook",
                "phase": "after_tool",
                "payload": {
                    "tool_name": "read_file",
                    "tool_call_id": "call-1",
                    "capability_id": "read_file",
                    "success": True,
                },
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


def test_full_auto_flag_accepted_by_run_parser() -> None:
    client_main = importlib.import_module("client.main")
    parser = client_main._build_parser()
    args = parser.parse_args(["run", "--task", "hello", "--full-auto"])
    assert args.full_auto is True


def test_full_auto_flag_defaults_to_false() -> None:
    client_main = importlib.import_module("client.main")
    parser = client_main._build_parser()
    args = parser.parse_args(["run", "--task", "hello"])
    assert args.full_auto is False


def test_auto_user_input_handler_picks_first_option() -> None:
    from dare_framework.tool._internal.tools.ask_user import AutoUserInputHandler

    handler = AutoUserInputHandler()
    questions = [
        {
            "question": "Which approach?",
            "header": "Approach",
            "options": [
                {"label": "Option A", "description": "First"},
                {"label": "Option B", "description": "Second"},
            ],
        }
    ]
    answers = asyncio.run(handler.handle(questions))
    assert answers["Which approach?"] == "Option A"


def test_auto_user_input_handler_uses_default_when_no_options() -> None:
    from dare_framework.tool._internal.tools.ask_user import AutoUserInputHandler

    handler = AutoUserInputHandler()
    questions = [{"question": "What now?", "header": "Q", "options": []}]
    answers = asyncio.run(handler.handle(questions))
    assert answers["What now?"] == AutoUserInputHandler.DEFAULT_RESPONSE


def test_auto_user_input_handler_custom_default() -> None:
    from dare_framework.tool._internal.tools.ask_user import AutoUserInputHandler

    handler = AutoUserInputHandler(default_response="YOLO")
    questions = [{"question": "What now?", "header": "Q", "options": []}]
    answers = asyncio.run(handler.handle(questions))
    assert answers["What now?"] == "YOLO"


def test_run_approval_policy_auto_approve_all() -> None:
    """When auto_approve_all is True, _RunApprovalPolicy approves any tool."""
    client_main = importlib.import_module("client.main")

    # Build a minimal mock for action_client, output, and watch
    class _FakeActionClient:
        def __init__(self):
            self.invocations = []

        async def invoke_action(self, action, **kwargs):
            self.invocations.append((action, kwargs))

    class _FakeOutput:
        def __init__(self):
            self.messages = []

        def info(self, msg):
            self.messages.append(msg)

        def ok(self, msg):
            self.messages.append(msg)

        def display(self, msg, level="info"):
            self.messages.append(msg)

    fake_client = _FakeActionClient()
    fake_output = _FakeOutput()
    watch = client_main._ApprovalWatchState()

    policy = client_main._RunApprovalPolicy(
        action_client=fake_client,
        output=fake_output,
        watch=watch,
        auto_approve_tools=set(),
        auto_approve_all=True,
    )

    # Even an unknown tool should be auto-approved
    asyncio.run(
        policy.on_pending("req-1", "dangerous_tool", "dangerous_tool")
    )
    assert len(fake_client.invocations) == 1
    assert fake_client.invocations[0][1]["request_id"] == "req-1"


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


def test_parser_accepts_system_prompt_flags() -> None:
    client_main = importlib.import_module("client.main")
    parser = client_main._build_parser()

    args = parser.parse_args(
        [
            "--system-prompt-mode",
            "append",
            "--system-prompt-text",
            "always respond in chinese",
            "run",
            "--task",
            "summarize readme",
        ]
    )

    assert args.system_prompt_mode == "append"
    assert args.system_prompt_text == "always respond in chinese"
    assert args.system_prompt_file is None


def test_run_and_script_parser_accept_control_stdin_flag() -> None:
    client_main = importlib.import_module("client.main")
    parser = client_main._build_parser()

    run_args = parser.parse_args(["run", "--task", "summarize readme", "--headless", "--control-stdin"])
    script_args = parser.parse_args(
        ["script", "--file", "tasks.txt", "--headless", "--control-stdin"]
    )

    assert run_args.control_stdin is True
    assert script_args.control_stdin is True


def test_chat_run_and_script_parser_accept_resume_flag() -> None:
    client_main = importlib.import_module("client.main")
    parser = client_main._build_parser()

    chat_args = parser.parse_args(["chat", "--resume"])
    run_args = parser.parse_args(["run", "--task", "summarize readme", "--resume", "session-42"])
    script_args = parser.parse_args(["script", "--file", "tasks.txt", "--resume"])

    assert chat_args.resume == "latest"
    assert run_args.resume == "session-42"
    assert script_args.resume == "latest"


def test_chat_run_and_script_parser_accept_session_id_flag() -> None:
    client_main = importlib.import_module("client.main")
    parser = client_main._build_parser()

    chat_args = parser.parse_args(["chat", "--session-id", "session-42"])
    run_args = parser.parse_args(["run", "--task", "summarize readme", "--session-id", "session-42"])
    script_args = parser.parse_args(["script", "--file", "tasks.txt", "--session-id", "session-42"])

    assert chat_args.session_id == "session-42"
    assert run_args.session_id == "session-42"
    assert script_args.session_id == "session-42"


def test_sessions_parser_accepts_list_subcommand() -> None:
    client_main = importlib.import_module("client.main")
    parser = client_main._build_parser()

    args = parser.parse_args(["sessions", "list"])

    assert args.command == "sessions"
    assert args.sessions_cmd == "list"


def test_chat_parser_rejects_control_stdin_flag() -> None:
    client_main = importlib.import_module("client.main")
    parser = client_main._build_parser()

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["chat", "--control-stdin"])

    assert excinfo.value.code == 2


def test_read_control_stdin_line_cancellation_does_not_block_default_executor_shutdown(
    monkeypatch,
) -> None:
    client_main = importlib.import_module("client.main")
    entered = threading.Event()
    release = threading.Event()

    class _BlockingStdin:
        def readline(self) -> str:
            entered.set()
            release.wait(timeout=5.0)
            return ""

    async def _exercise() -> None:
        task = asyncio.create_task(client_main._read_control_stdin_line())
        deadline = time.time() + 1.0
        while not entered.is_set():
            assert time.time() < deadline
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    monkeypatch.setattr(client_main.sys, "stdin", _BlockingStdin())

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(asyncio.wait_for(_exercise(), timeout=1.0))
        loop.run_until_complete(asyncio.wait_for(loop.shutdown_default_executor(), timeout=0.2))
    finally:
        release.set()
        with contextlib.suppress(Exception):
            loop.run_until_complete(asyncio.wait_for(loop.shutdown_default_executor(), timeout=1.0))
        loop.close()


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


@pytest.mark.asyncio
async def test_main_run_control_stdin_requires_headless(monkeypatch, tmp_path, capsys) -> None:
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
        raise AssertionError("bootstrap_runtime should not run for invalid control-stdin args")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "run",
            "--task",
            "summarize readme",
            "--control-stdin",
        ]
    )

    assert rc == 2
    output = capsys.readouterr().out
    assert "--control-stdin requires --headless" in output


@pytest.mark.asyncio
async def test_main_rejects_system_prompt_text_and_file_together(monkeypatch, tmp_path, capsys) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    prompt_file = tmp_path / "system_prompt.txt"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text("prompt", encoding="utf-8")

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
        raise AssertionError("bootstrap_runtime should not run for invalid prompt args")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--system-prompt-text",
            "inline prompt",
            "--system-prompt-file",
            str(prompt_file),
            "run",
            "--task",
            "summarize readme",
        ]
    )

    assert rc == 2
    output = capsys.readouterr().out
    assert "--system-prompt-text and --system-prompt-file are mutually exclusive" in output


@pytest.mark.asyncio
async def test_main_script_control_stdin_requires_headless(monkeypatch, tmp_path, capsys) -> None:
    client_main = importlib.import_module("client.main")
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    script_path = tmp_path / "tasks.txt"
    script_path.write_text("task one\n", encoding="utf-8")

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
        raise AssertionError("bootstrap_runtime should not run for invalid control-stdin args")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "script",
            "--file",
            str(script_path),
            "--control-stdin",
        ]
    )

    assert rc == 2
    output = capsys.readouterr().out
    assert "--control-stdin requires --headless" in output


@pytest.mark.asyncio
async def test_main_run_resume_missing_session_returns_two(monkeypatch, tmp_path, capsys) -> None:
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

    class _FakeContext:
        def stm_get(self):  # noqa: ANN201
            return []

        def stm_add(self, _message):  # noqa: ANN001, ANN201
            return None

        def stm_clear(self):  # noqa: ANN201
            return []

    class _FakeRuntime:
        def __init__(self) -> None:
            self.agent = type("Agent", (), {"context": _FakeContext()})()
            self.channel = object()
            self.model = object()
            self.config = config
            self.client_channel = object()

        async def close(self) -> None:
            return None

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return _FakeRuntime()

    async def _unexpected_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        raise AssertionError("run_task should not execute when resume target is missing")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _unexpected_run_task)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "run",
            "--resume",
            "latest",
            "--task",
            "continue previous task",
        ]
    )

    assert rc == 2
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["type"] == "log"
    assert payload["level"] == "error"
    assert "resume" in payload["message"]


@pytest.mark.asyncio
async def test_main_run_rejects_conflicting_resume_and_session_id(monkeypatch, tmp_path, capsys) -> None:
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

    async def _unexpected_bootstrap(_options):  # noqa: ANN001
        raise AssertionError("bootstrap_runtime should not run when argparse rejects removed flags")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _unexpected_bootstrap)

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
            "continue previous task",
            "--resume",
            "session-a",
            "--session-id",
            "session-b",
        ]
    )

    assert rc == 2
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["type"] == "log"
    assert payload["level"] == "error"
    assert "--resume" in payload["message"]
    assert "--session-id" in payload["message"]


@pytest.mark.asyncio
async def test_dispatch_control_action_session_resume_restores_history(tmp_path) -> None:
    client_main = importlib.import_module("client.main")
    store = importlib.import_module("client.session_store")
    workspace = tmp_path / "workspace"
    session_store = store.ClientSessionStore(workspace)

    runtime_context_messages: list[Message] = []

    class _FakeContext:
        def stm_get(self):  # noqa: ANN201
            return list(runtime_context_messages)

        def stm_add(self, message):  # noqa: ANN001, ANN201
            runtime_context_messages.append(message)
            return None

        def stm_clear(self):  # noqa: ANN201
            runtime_context_messages.clear()
            return []

    runtime = type("Runtime", (), {"agent": type("Agent", (), {"context": _FakeContext()})()})()
    state = client_main.CLISessionState(conversation_id="fresh-session", mode=client_main.ExecutionMode.EXECUTE)

    snapshot_state = client_main.CLISessionState(conversation_id="session-42", mode=client_main.ExecutionMode.PLAN)
    session_store.save(
        state=snapshot_state,
        messages=[
            Message(role="user", text="history-user"),
            Message(role="assistant", text="history-assistant"),
        ],
    )

    result = await client_main._dispatch_control_action(
        action_id="session:resume",
        params={"session_id": "session-42"},
        state=state,
        runtime=runtime,
        action_client=object(),
        session_store=session_store,
    )

    assert result["session_id"] == "session-42"
    assert result["restored_messages"] == 2
    assert state.conversation_id == "session-42"
    assert state.mode == client_main.ExecutionMode.PLAN
    assert [item.text for item in runtime_context_messages] == ["history-user", "history-assistant"]


@pytest.mark.asyncio
async def test_dispatch_control_action_session_resume_rejects_running_state(tmp_path) -> None:
    client_main = importlib.import_module("client.main")
    store = importlib.import_module("client.session_store")
    workspace = tmp_path / "workspace"
    session_store = store.ClientSessionStore(workspace)
    state = client_main.CLISessionState(
        conversation_id="session-live",
        mode=client_main.ExecutionMode.EXECUTE,
    )
    state.status = client_main.SessionStatus.RUNNING

    with pytest.raises(client_main.ActionClientError) as excinfo:
        await client_main._dispatch_control_action(
            action_id="session:resume",
            params={"session_id": "session-42"},
            state=state,
            runtime=object(),
            action_client=object(),
            session_store=session_store,
        )

    assert excinfo.value.code == "INVALID_SESSION_STATE"
    assert excinfo.value.target == "session:resume"


@pytest.mark.asyncio
async def test_run_control_stdin_loop_updates_headless_context_after_session_resume(monkeypatch, tmp_path) -> None:
    client_main = importlib.import_module("client.main")
    store = importlib.import_module("client.session_store")
    workspace = tmp_path / "workspace"
    session_store = store.ClientSessionStore(workspace)

    class _FakeContext:
        def __init__(self) -> None:
            self._messages: list[Message] = []

        def stm_get(self) -> list[Message]:
            return list(self._messages)

        def stm_add(self, message: Message) -> None:
            self._messages.append(message)

        def stm_clear(self) -> list[Message]:
            self._messages.clear()
            return []

    runtime = type("Runtime", (), {"agent": type("Agent", (), {"context": _FakeContext()})()})()
    state = client_main.CLISessionState(conversation_id="fresh-session", mode=client_main.ExecutionMode.EXECUTE)
    snapshot_state = client_main.CLISessionState(conversation_id="session-42", mode=client_main.ExecutionMode.PLAN)
    session_store.save(
        state=snapshot_state,
        messages=[Message(role="user", text="history-user")],
    )
    output = client_main.OutputFacade("headless")
    output.set_protocol_context(session_id="fresh-session", run_id="fresh-session")

    frames = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-1",
                    "action": "session:resume",
                    "params": {"session_id": "session-42"},
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return next(frames)

    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    await client_main._run_control_stdin_loop(
        state=state,
        runtime=runtime,
        action_client=object(),
        session_store=session_store,
        output=output,
    )

    assert output._headless is not None
    assert output._headless._session_id == "session-42"
    assert output._headless._run_id == "session-42"
    assert state.conversation_id == "session-42"


def test_client_session_store_persists_canonical_message_schema(tmp_path) -> None:
    store = importlib.import_module("client.session_store")
    workspace = tmp_path / "workspace"
    session_store = store.ClientSessionStore(workspace)
    client_main = importlib.import_module("client.main")

    state = client_main.CLISessionState(conversation_id="session-rich", mode=client_main.ExecutionMode.EXECUTE)
    session_store.save(
        state=state,
        messages=[
            Message(
                role="user",
                kind="chat",
                text="look at these",
                attachments=[
                    {
                        "kind": "image",
                        "uri": "https://example.com/a.png",
                        "mime_type": "image/png",
                    }
                ],
                data={"album": "demo"},
                metadata={"source": "test"},
                id="msg-1",
            )
        ],
    )

    raw = json.loads(session_store.path_for("session-rich").read_text(encoding="utf-8"))
    message = raw["messages"][0]
    assert "content" not in message
    assert message["role"] == "user"
    assert message["kind"] == "chat"
    assert message["text"] == "look at these"
    assert message["attachments"][0]["kind"] == "image"
    assert message["attachments"][0]["uri"] == "https://example.com/a.png"
    assert message["data"] == {"album": "demo"}

    restored = session_store.load("session-rich").messages[0]
    assert restored.kind == "chat"
    assert restored.text == "look at these"
    assert restored.attachments[0].uri == "https://example.com/a.png"
    assert restored.data == {"album": "demo"}


def test_client_session_store_rejects_traversal_session_ids(tmp_path) -> None:
    store = importlib.import_module("client.session_store")
    session_store = store.ClientSessionStore(tmp_path / "workspace")

    with pytest.raises(store.SessionStoreError, match="invalid session_id"):
        session_store.path_for("../../escape")

    with pytest.raises(store.SessionStoreError, match="invalid session_id"):
        session_store.path_for("session/../../escape")


def test_client_session_store_rejects_tampered_snapshot_session_id(tmp_path) -> None:
    store = importlib.import_module("client.session_store")
    workspace = tmp_path / "workspace"
    session_store = store.ClientSessionStore(workspace)
    tampered = session_store.session_dir / "tampered.json"
    tampered.write_text(
        json.dumps(
            {
                "schema_version": store.SESSION_SNAPSHOT_SCHEMA_VERSION,
                "session_id": "../../escape",
                "mode": "execute",
                "created_at": 1,
                "updated_at": 2,
                "workspace_dir": str(workspace),
                "messages": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(store.SessionStoreError, match="invalid session_id"):
        session_store.load("tampered")

    assert session_store.list_sessions() == []


@pytest.mark.asyncio
async def test_main_sessions_list_returns_sorted_session_summaries(monkeypatch, tmp_path, capsys) -> None:
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

    store = importlib.import_module("client.session_store")
    session_store = store.ClientSessionStore(workspace)
    state_a = client_main.CLISessionState(conversation_id="session-a")
    state_b = client_main.CLISessionState(conversation_id="session-b")
    session_store.save(
        state=state_a,
        messages=[Message(role="user", text="older")],
    )
    session_store.save(
        state=state_b,
        messages=[
            Message(role="user", text="newer"),
            Message(role="assistant", text="done"),
        ],
    )

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _unexpected_bootstrap(_options):  # noqa: ANN001
        raise AssertionError("bootstrap_runtime should not run for sessions list")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _unexpected_bootstrap)

    rc = await client_main.main(
        [
            "--workspace",
            str(workspace),
            "--user-dir",
            str(user_dir),
            "--output",
            "json",
            "sessions",
            "list",
        ]
    )

    assert rc == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["type"] == "result"
    assert [entry["session_id"] for entry in payload["data"]["sessions"]] == ["session-b", "session-a"]
    assert payload["data"]["sessions"][0]["messages_count"] == 2
