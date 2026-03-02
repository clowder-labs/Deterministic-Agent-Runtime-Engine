from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from dare_framework.config import Config


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


class _FakeActionClient:
    calls: list[tuple[str, dict[str, Any]]] = []

    def __init__(self, channel: Any, *, timeout_seconds: float = 30.0) -> None:
        _ = (channel, timeout_seconds)

    async def invoke_action(self, action: Any, **params: Any) -> dict[str, Any]:
        action_id = action.value if hasattr(action, "value") else str(action)
        type(self).calls.append((action_id, dict(params)))
        if action_id == "approvals:list":
            return {"pending": [], "rules": []}
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
