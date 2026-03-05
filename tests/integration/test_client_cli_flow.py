from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from dare_framework.config import Config
from dare_framework.context import Message


class _FakeClientChannel:
    def __init__(self, *, events: list[dict[str, Any]] | None = None) -> None:
        self._events = list(events or [])

    async def poll(self, timeout: float | None = None):  # noqa: ANN001
        _ = timeout
        await asyncio.sleep(0)
        if self._events:
            return SimpleNamespace(payload=self._events.pop(0))
        return None


class _FakeRuntime:
    def __init__(self, *, config: Config, events: list[dict[str, Any]] | None = None) -> None:
        self.config = config
        self.model = object()
        self.channel = object()
        self.agent = object()
        self.client_channel = _FakeClientChannel(events=events)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakeContext:
    def __init__(self) -> None:
        self._messages: list[Message] = []

    def stm_add(self, message: Message) -> None:
        self._messages.append(message)

    def stm_get(self) -> list[Message]:
        return list(self._messages)

    def stm_clear(self) -> list[Message]:
        self._messages.clear()
        return []


class _FakeAgent:
    def __init__(self) -> None:
        self.context = _FakeContext()


class _FakeActionClient:
    calls: list[tuple[str, dict[str, Any]]] = []

    def __init__(self, channel: Any, *, timeout_seconds: float = 30.0) -> None:
        _ = (channel, timeout_seconds)

    async def invoke_action(self, action: Any, **params: Any) -> dict[str, Any]:
        action_id = action.value if hasattr(action, "value") else str(action)
        type(self).calls.append((action_id, dict(params)))
        if action_id == "approvals:list":
            return {"pending": [], "rules": []}
        if action_id == "skills:list":
            return {"skills": [{"name": "development-workflow"}]}
        if action_id == "mcp:list":
            return {"mcps": ["demo"], "mcp_paths": ["/tmp/demo"], "tools": []}
        if action_id == "mcp:reload":
            return {"ok": True, "reloaded": params.get("mcp_name") or "all"}
        if action_id == "mcp:show-tool":
            return {
                "found": True,
                "tool": {
                    "name": params.get("tool_name", "?"),
                    "mcp_name": params.get("mcp_name", "?"),
                },
            }
        return {"ok": True}

    async def invoke_control(self, control: Any, **params: Any) -> dict[str, Any]:
        control_id = control.value if hasattr(control, "value") else str(control)
        return {"control": control_id, "params": dict(params)}


def _config_for_tests(tmp_path: Path) -> Config:
    workspace = tmp_path / "workspace"
    user_dir = tmp_path / "user"
    workspace.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    return Config.from_dict(
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


@pytest.mark.asyncio
async def test_main_script_returns_nonzero_when_execution_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _FailResult:
        success = False
        output = None
        errors = ["boom"]

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        return _FailResult()

    script_path = tmp_path / "fail_script.txt"
    script_path.write_text("run one failing task\n", encoding="utf-8")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "TransportActionClient", _FakeActionClient)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "script",
            "--file",
            str(script_path),
        ]
    )
    assert rc == 1
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_human_logs_to_default_file_and_keeps_stdout_to_task_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        return _OkResult()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
        ]
    )

    output = capsys.readouterr().out
    log_path = tmp_path / "dare.log"

    assert rc == 0
    assert output.strip() == "assistant says hi"
    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert "workspace=" in log_text
    assert "task completed" in log_text
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_emits_lifecycle_frames(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        return _OkResult()

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert rc == 0
    assert [line["event"] for line in lines[:3]] == [
        "session.started",
        "task.started",
        "task.completed",
    ]
    assert all(line["schema_version"] == "client-headless-event-envelope.v1" for line in lines)
    assert len({line["run_id"] for line in lines}) == 1
    assert len({line["session_id"] for line in lines}) == 1
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_control_stdin_status_get_emits_structured_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    control_lines = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-1",
                    "action": "status:get",
                    "params": {},
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return next(control_lines)

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    headless_events = [line for line in lines if line["schema_version"] == "client-headless-event-envelope.v1"]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert [line["event"] for line in headless_events[:3]] == [
        "session.started",
        "task.started",
        "task.completed",
    ]
    assert len(control_frames) == 1
    assert control_frames[0]["id"] == "ctl-1"
    assert control_frames[0]["ok"] is True
    assert control_frames[0]["result"]["mode"] == "execute"
    assert control_frames[0]["result"]["status"] == "running"
    assert control_frames[0]["result"]["running"] is True
    assert control_frames[0]["result"]["active_task"] == "do one task"
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_control_stdin_status_get_reports_pending_approvals(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    pending_event = {
        "type": "approval_pending",
        "resp": {
            "request": {"request_id": "req-status-pending-1"},
            "capability_id": "run_command",
        },
    }
    runtime = _FakeRuntime(config=config, events=[pending_event])

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.4)
        return _OkResult()

    approval_seen = asyncio.Event()
    original_on_transport_event = client_main._on_transport_event

    async def _observed_on_transport_event(payload, *, output, **kwargs):  # noqa: ANN001
        await original_on_transport_event(payload, output=output, **kwargs)
        if payload.get("type") == "approval_pending":
            approval_seen.set()

    control_sent = False

    async def _fake_read_control_stdin_line() -> str | None:
        nonlocal control_sent
        if control_sent:
            await asyncio.sleep(0)
            return None
        await approval_seen.wait()
        control_sent = True
        return json.dumps(
            {
                "schema_version": "client-control-stdin.v1",
                "id": "ctl-status-pending-1",
                "action": "status:get",
                "params": {},
            }
        )

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(client_main, "_on_transport_event", _observed_on_transport_event)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--control-stdin",
            "--approval-timeout-seconds",
            "2.0",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert len(control_frames) == 1
    assert control_frames[0]["id"] == "ctl-status-pending-1"
    assert control_frames[0]["ok"] is True
    assert control_frames[0]["result"]["pending_approvals"] == ["req-status-pending-1"]
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_control_stdin_bridges_approvals_list(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    control_lines = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-approvals-1",
                    "action": "approvals:list",
                    "params": {},
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return next(control_lines)

    _FakeActionClient.calls = []
    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "TransportActionClient", _FakeActionClient)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert len(control_frames) == 1
    assert control_frames[0]["id"] == "ctl-approvals-1"
    assert control_frames[0]["ok"] is True
    assert control_frames[0]["result"] == {"pending": [], "rules": []}
    assert any(action_id == "approvals:list" for action_id, _ in _FakeActionClient.calls)
    assert runtime.closed is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action_id", "params", "expected_result", "expected_call"),
    [
        (
            "actions:list",
            {},
            {
                "actions": [
                    "actions:list",
                    "approvals:deny",
                    "approvals:grant",
                    "approvals:list",
                    "approvals:poll",
                    "approvals:revoke",
                    "mcp:list",
                    "mcp:reload",
                    "mcp:show-tool",
                    "session:resume",
                    "skills:list",
                    "status:get",
                ]
            },
            None,
        ),
        (
            "skills:list",
            {},
            {"skills": [{"name": "development-workflow"}]},
            ("skills:list", {}),
        ),
        (
            "mcp:list",
            {"mcp_name": "demo"},
            {"mcps": ["demo"], "mcp_paths": ["/tmp/demo"], "tools": []},
            ("mcp:list", {"mcp_name": "demo"}),
        ),
        (
            "mcp:reload",
            {"mcp_name": "demo"},
            {"ok": True, "reloaded": "demo"},
            ("mcp:reload", {"mcp_name": "demo"}),
        ),
        (
            "mcp:show-tool",
            {"mcp_name": "demo", "tool_name": "search"},
            {"found": True, "tool": {"name": "search", "mcp_name": "demo"}},
            ("mcp:show-tool", {"mcp_name": "demo", "tool_name": "search"}),
        ),
    ],
)
async def test_main_run_headless_control_stdin_bridges_additional_host_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    action_id: str,
    params: dict[str, Any],
    expected_result: dict[str, Any],
    expected_call: tuple[str, dict[str, Any]],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    control_lines = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": f"ctl-{action_id}-1",
                    "action": action_id,
                    "params": params,
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return next(control_lines)

    _FakeActionClient.calls = []
    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "TransportActionClient", _FakeActionClient)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert len(control_frames) == 1
    assert control_frames[0]["id"] == f"ctl-{action_id}-1"
    assert control_frames[0]["ok"] is True
    assert control_frames[0]["result"] == expected_result
    if expected_call is None:
        assert _FakeActionClient.calls == []
    else:
        assert expected_call in _FakeActionClient.calls
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_script_headless_control_stdin_status_get_reports_active_task(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    control_lines = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-script-status-1",
                    "action": "status:get",
                    "params": {},
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return next(control_lines)

    script_path = tmp_path / "headless-control.script.txt"
    script_path.write_text("task one\n", encoding="utf-8")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "script",
            "--file",
            str(script_path),
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert len(control_frames) == 1
    assert control_frames[0]["id"] == "ctl-script-status-1"
    assert control_frames[0]["ok"] is True
    assert control_frames[0]["result"]["status"] == "running"
    assert control_frames[0]["result"]["running"] is True
    assert control_frames[0]["result"]["active_task"] == "task one"
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_script_headless_control_stdin_bridges_actions_list(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    control_lines = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-script-actions-1",
                    "action": "actions:list",
                    "params": {},
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return next(control_lines)

    script_path = tmp_path / "headless-actions.script.txt"
    script_path.write_text("task one\n", encoding="utf-8")

    _FakeActionClient.calls = []
    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "TransportActionClient", _FakeActionClient)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "script",
            "--file",
            str(script_path),
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert len(control_frames) == 1
    assert control_frames[0]["id"] == "ctl-script-actions-1"
    assert control_frames[0]["ok"] is True
    assert "actions:list" in control_frames[0]["result"]["actions"]
    assert "session:resume" in control_frames[0]["result"]["actions"]
    assert _FakeActionClient.calls == []
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_control_stdin_actions_list_coexists_with_existing_control_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    control_lines = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-actions-1",
                    "action": "actions:list",
                    "params": {},
                }
            ),
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-approvals-2",
                    "action": "approvals:list",
                    "params": {},
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return next(control_lines)

    _FakeActionClient.calls = []
    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "TransportActionClient", _FakeActionClient)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert [frame["id"] for frame in control_frames] == ["ctl-actions-1", "ctl-approvals-2"]
    assert control_frames[0]["ok"] is True
    assert "actions:list" in control_frames[0]["result"]["actions"]
    assert "session:resume" in control_frames[0]["result"]["actions"]
    assert control_frames[1]["ok"] is True
    assert control_frames[1]["result"] == {"pending": [], "rules": []}
    assert _FakeActionClient.calls == [("approvals:list", {})]
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_control_stdin_session_resume_rejects_running_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    control_lines = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-session-resume-1",
                    "action": "session:resume",
                    "params": {"session_id": "session-42"},
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0.05)
        return next(control_lines)

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert len(control_frames) == 1
    assert control_frames[0]["id"] == "ctl-session-resume-1"
    assert control_frames[0]["ok"] is False
    assert control_frames[0]["error"]["code"] == "INVALID_SESSION_STATE"
    assert control_frames[0]["error"]["target"] == "session:resume"
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_control_stdin_does_not_emit_startup_handshake_without_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return None

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    headless_events = [line for line in lines if line["schema_version"] == "client-headless-event-envelope.v1"]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert [line["event"] for line in headless_events[:3]] == [
        "session.started",
        "task.started",
        "task.completed",
    ]
    assert control_frames == []
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_control_stdin_rejects_unsupported_action(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    control_lines = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-unsupported-1",
                    "action": "mcp:unload",
                    "params": {},
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return next(control_lines)

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert len(control_frames) == 1
    assert control_frames[0]["id"] == "ctl-unsupported-1"
    assert control_frames[0]["ok"] is False
    assert control_frames[0]["error"]["code"] == "UNSUPPORTED_ACTION"
    assert control_frames[0]["error"]["target"] == "mcp:unload"
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_control_stdin_surfaces_action_handler_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    class _FailingActionClient(_FakeActionClient):
        async def invoke_action(self, action: Any, **params: Any) -> dict[str, Any]:
            action_id = action.value if hasattr(action, "value") else str(action)
            type(self).calls.append((action_id, dict(params)))
            raise client_main.ActionClientError(
                code="ACTION_HANDLER_FAILED",
                reason="approval backend unavailable",
                target=action_id,
            )

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.2)
        return _OkResult()

    control_lines = iter(
        [
            json.dumps(
                {
                    "schema_version": "client-control-stdin.v1",
                    "id": "ctl-approvals-fail-1",
                    "action": "approvals:list",
                    "params": {},
                }
            ),
            None,
        ]
    )

    async def _fake_read_control_stdin_line() -> str | None:
        await asyncio.sleep(0)
        return next(control_lines)

    _FailingActionClient.calls = []
    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "TransportActionClient", _FailingActionClient)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.setattr(
        client_main,
        "_read_control_stdin_line",
        _fake_read_control_stdin_line,
        raising=False,
    )

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--control-stdin",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    control_frames = [line for line in lines if line["schema_version"] == "client-control-stdin.v1"]

    assert rc == 0
    assert len(control_frames) == 1
    assert control_frames[0]["id"] == "ctl-approvals-fail-1"
    assert control_frames[0]["ok"] is False
    assert control_frames[0]["error"]["code"] == "ACTION_HANDLER_FAILED"
    assert control_frames[0]["error"]["target"] == "approvals:list"
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_doctor_human_uses_configured_log_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    custom_log_path = tmp_path / "logs" / "cli.log"
    config = Config.from_dict(
        {
            **_config_for_tests(tmp_path).to_dict(),
            "cli": {"log_path": str(custom_log_path)},
        }
    )

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _forbidden_bootstrap(_options):  # noqa: ANN001
        raise AssertionError("doctor should not bootstrap runtime")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _forbidden_bootstrap)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "doctor",
        ]
    )

    output = capsys.readouterr().out
    default_log_path = tmp_path / "dare.log"

    assert rc == 0
    assert '"ok": true' in output or '"ok": false' in output
    assert custom_log_path.exists()
    assert default_log_path.exists() is False
    assert "DARE CLIENT CLI" in custom_log_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_main_script_allows_approvals_command_while_task_running(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "ok"}
        errors = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.02)
        return _OkResult()

    _FakeActionClient.calls = []
    script_path = tmp_path / "approvals_script.txt"
    script_path.write_text(
        "\n".join(
            [
                "start background task",
                "/approvals list",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "TransportActionClient", _FakeActionClient)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "script",
            "--file",
            str(script_path),
        ]
    )
    assert rc == 0
    assert any(action_id == "approvals:list" for action_id, _ in _FakeActionClient.calls)


@pytest.mark.asyncio
async def test_main_doctor_does_not_call_bootstrap_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _forbidden_bootstrap(_options):  # noqa: ANN001
        raise AssertionError("doctor should not bootstrap runtime")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _forbidden_bootstrap)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "doctor",
        ]
    )
    assert rc == 0


@pytest.mark.asyncio
async def test_main_run_times_out_when_approval_pending(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    pending_event = {
        "type": "approval_pending",
        "resp": {
            "request": {"request_id": "req-timeout-1"},
            "capability_id": "run_command",
        },
    }
    runtime = _FakeRuntime(config=config, events=[pending_event])

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(1.0)
        return type("OkResult", (), {"success": True, "output": {"content": "ok"}, "errors": []})()

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--approval-timeout-seconds",
            "0.2",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 1
    assert "approval pending: request_id=req-timeout-1" in output
    assert "approval wait timed out" in output
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_headless_times_out_with_structured_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    pending_event = {
        "type": "approval_pending",
        "resp": {
            "request": {"request_id": "req-timeout-headless-1"},
            "capability_id": "run_command",
        },
    }
    runtime = _FakeRuntime(config=config, events=[pending_event])

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(1.0)
        return type("OkResult", (), {"success": True, "output": {"content": "ok"}, "errors": []})()

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--headless",
            "--approval-timeout-seconds",
            "0.2",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    events = [line["event"] for line in lines]

    assert rc == 1
    assert "approval.pending" in events
    assert events[-1] == "task.failed"
    assert lines[-1]["data"]["request_id"] == "req-timeout-headless-1"
    assert "approval wait timed out" in lines[-1]["data"]["error"]
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_script_headless_times_out_with_structured_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    pending_event = {
        "type": "approval_pending",
        "resp": {
            "request": {"request_id": "req-script-headless-timeout-1"},
            "capability_id": "run_command",
        },
    }
    runtime = _FakeRuntime(config=config, events=[pending_event])

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(1.0)
        return type("OkResult", (), {"success": True, "output": {"content": "ok"}, "errors": []})()

    script_path = tmp_path / "headless-timeout.script.txt"
    script_path.write_text("do one task\n", encoding="utf-8")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "script",
            "--file",
            str(script_path),
            "--headless",
            "--approval-timeout-seconds",
            "0.2",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    events = [line["event"] for line in lines]

    assert rc == 1
    assert "approval.pending" in events
    assert events[-1] == "task.failed"
    assert lines[-1]["data"]["request_id"] == "req-script-headless-timeout-1"
    assert "approval wait timed out" in lines[-1]["data"]["error"]
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_script_headless_resets_timeout_watch_between_tasks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    pending_event = {
        "type": "approval_pending",
        "resp": {
            "request": {"request_id": "req-script-headless-reset-1"},
            "capability_id": "run_command",
        },
    }
    runtime = _FakeRuntime(config=config, events=[pending_event])

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "ok"}
        errors: list[str] = []

    calls: list[str] = []

    async def _script_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        calls.append(task_text)
        await asyncio.sleep(1.0 if len(calls) == 1 else 0.1)
        return _OkResult()

    script_path = tmp_path / "headless-reset.script.txt"
    script_path.write_text("task one\ntask two\n", encoding="utf-8")

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _script_run_task)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "script",
            "--file",
            str(script_path),
            "--headless",
            "--approval-timeout-seconds",
            "0.2",
        ]
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    task_events = [(line["event"], line["data"].get("task")) for line in lines if line["event"].startswith("task.")]

    assert rc == 1
    assert task_events == [
        ("task.started", "task one"),
        ("task.failed", "task one"),
        ("task.started", "task two"),
        ("task.completed", "task two"),
    ]
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_auto_approves_configured_tool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    pending_event = {
        "type": "approval_pending",
        "resp": {
            "request": {"request_id": "req-auto-1"},
            "capability_id": "run_command",
            "tool_name": "run_command",
        },
    }
    runtime = _FakeRuntime(config=config, events=[pending_event])

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return runtime

    class _OkResult:
        success = True
        output = {"content": "done"}
        errors: list[str] = []

    async def _slow_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = (agent, task_text, conversation_id, transport)
        await asyncio.sleep(0.4)
        return _OkResult()

    _FakeActionClient.calls = []
    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "TransportActionClient", _FakeActionClient)
    monkeypatch.setattr(client_main, "run_task", _slow_run_task)
    monkeypatch.chdir(tmp_path)

    rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "do one task",
            "--approval-timeout-seconds",
            "0.2",
            "--auto-approve-tool",
            "run_command",
        ]
    )
    output = capsys.readouterr().out
    log_text = (tmp_path / "dare.log").read_text(encoding="utf-8")
    assert rc == 0
    assert "auto-approving request_id=req-auto-1 for tool=run_command" not in output
    assert "auto-approving request_id=req-auto-1 for tool=run_command" in log_text
    assert any(action_id == "approvals:grant" for action_id, _ in _FakeActionClient.calls)
    assert runtime.closed is True


@pytest.mark.asyncio
async def test_main_run_resume_latest_restores_history_and_session_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    runtimes: list[_FakeRuntime] = []
    seen_histories: list[list[str]] = []
    seen_session_ids: list[str | None] = []

    class _ResumeRuntime(_FakeRuntime):
        def __init__(self, *, config: Config) -> None:
            super().__init__(config=config)
            self.agent = _FakeAgent()

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        runtime = _ResumeRuntime(config=config)
        runtimes.append(runtime)
        return runtime

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = transport
        seen_histories.append([message.content for message in agent.context.stm_get()])
        seen_session_ids.append(conversation_id)
        agent.context.stm_add(Message(role="user", content=task_text))
        agent.context.stm_add(Message(role="assistant", content=f"done:{task_text}"))
        return _OkResult()

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)

    first_rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "first task",
        ]
    )
    assert first_rc == 0

    session_dir = Path(config.workspace_dir) / ".dare" / "sessions"
    session_files = list(session_dir.glob("*.json"))
    assert len(session_files) == 1

    second_rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--resume",
            "latest",
            "--task",
            "follow up",
        ]
    )

    assert second_rc == 0
    assert seen_histories[0] == []
    assert seen_histories[1] == ["first task", "done:first task"]
    assert seen_session_ids[0]
    assert seen_session_ids[1] == seen_session_ids[0]
    assert len(runtimes) == 2
    assert all(runtime.closed is True for runtime in runtimes)


@pytest.mark.asyncio
async def test_main_run_resume_specific_session_restores_history(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client_main = importlib.import_module("client.main")
    config = _config_for_tests(tmp_path)
    seen_histories: list[list[str]] = []
    seen_session_ids: list[str | None] = []

    class _ResumeRuntime(_FakeRuntime):
        def __init__(self, *, config: Config) -> None:
            super().__init__(config=config)
            self.agent = _FakeAgent()

    def _fake_load_effective_config(_options):  # noqa: ANN001
        return object(), config

    async def _fake_bootstrap_runtime(_options):  # noqa: ANN001
        return _ResumeRuntime(config=config)

    class _OkResult:
        success = True
        output = {"content": "assistant says hi"}
        errors: list[str] = []

    async def _fake_run_task(*, agent, task_text, conversation_id=None, transport=None):  # noqa: ANN001
        _ = transport
        seen_histories.append([message.content for message in agent.context.stm_get()])
        seen_session_ids.append(conversation_id)
        agent.context.stm_add(Message(role="user", content=task_text))
        agent.context.stm_add(Message(role="assistant", content=f"done:{task_text}"))
        return _OkResult()

    monkeypatch.setattr(client_main, "load_effective_config", _fake_load_effective_config)
    monkeypatch.setattr(client_main, "bootstrap_runtime", _fake_bootstrap_runtime)
    monkeypatch.setattr(client_main, "run_task", _fake_run_task)

    first_rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--task",
            "seed task",
        ]
    )
    assert first_rc == 0

    session_dir = Path(config.workspace_dir) / ".dare" / "sessions"
    session_files = list(session_dir.glob("*.json"))
    assert len(session_files) == 1
    session_id = session_files[0].stem

    second_rc = await client_main.main(
        [
            "--workspace",
            config.workspace_dir,
            "--user-dir",
            config.user_dir,
            "run",
            "--resume",
            session_id,
            "--task",
            "second task",
        ]
    )

    assert second_rc == 0
    assert seen_histories[1] == ["seed task", "done:seed task"]
    assert seen_session_ids[1] == session_id


@pytest.mark.asyncio
async def test_run_chat_script_sessions_list_emits_saved_sessions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_main = importlib.import_module("client.main")
    session_store_module = importlib.import_module("client.session_store")
    config = _config_for_tests(tmp_path)
    runtime = _FakeRuntime(config=config)
    runtime.agent = _FakeAgent()

    store = session_store_module.ClientSessionStore(config.workspace_dir)
    older_state = client_main.CLISessionState(conversation_id="session-older")
    newer_state = client_main.CLISessionState(conversation_id="session-newer")
    store.save(state=older_state, messages=[Message(role="user", content="older")])
    store.save(state=newer_state, messages=[Message(role="user", content="newer")])

    rc = await client_main._run_chat(
        runtime=runtime,
        action_client=object(),
        output=client_main.OutputFacade("json"),
        mode="execute",
        script_lines=["/sessions list", "/quit"],
        session_store=store,
    )

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    result_payloads = [line["data"] for line in lines if line.get("type") == "result"]

    assert rc == 0
    assert result_payloads
    assert [entry["session_id"] for entry in result_payloads[0]["sessions"]] == [
        "session-newer",
        "session-older",
    ]
