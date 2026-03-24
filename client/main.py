"""Unified external CLI for DARE framework."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

from client.session_store import ClientSessionStore, SessionSnapshot, SessionStoreError
from client.commands.approvals import approvals_usage_lines, handle_approvals_tokens
from client.commands.info import (
    build_doctor_report,
    list_skills,
    list_tools,
    send_control,
    show_config,
    show_model,
)
from client.commands.mcp import format_mcp_inspection, handle_mcp_tokens
from client.parser.command import Command, CommandType, parse_command
from client.render.control import ControlStdinRenderer
from client.render.headless import HeadlessRenderer
from client.render.human import HumanRenderer
from client.render.json import JsonRenderer
from client.runtime.action_client import ActionClientError, TransportActionClient
from client.runtime.bootstrap import RuntimeOptions, bootstrap_runtime, load_effective_config
from client.runtime.event_stream import EventPump
from client.runtime.logging_setup import CLI_LOGGER_NAME, configure_cli_logging, resolve_cli_log_path
from client.runtime.task_runner import format_run_output, preview_plan, run_task
from client.session import CLISessionState, ExecutionMode, SessionStatus
from dare_framework.model.default_model_adapter_manager import DefaultModelAdapterManager
from dare_framework.transport.interaction.resource_action import ResourceAction


class OutputFacade:
    """Output adapter for human and json modes."""

    def __init__(self, mode: str) -> None:
        self._mode = mode
        self._human = HumanRenderer() if mode == "human" else None
        self._json = JsonRenderer() if mode == "json" else None
        self._headless = HeadlessRenderer() if mode == "headless" else None
        self._logger = logging.getLogger(CLI_LOGGER_NAME)

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_headless(self) -> bool:
        return self._headless is not None

    def set_protocol_context(self, *, session_id: str, run_id: str) -> None:
        if self._headless is None:
            return
        self._headless.set_context(session_id=session_id, run_id=run_id)

    def _emit_headless(self, event: str, payload: Any) -> bool:
        if self._headless is None:
            return False
        self._headless.emit(event, _serialize(payload))
        return True

    def header(self, title: str) -> None:
        self._logger.info("%s", title)
        if self._human is not None:
            return
        if self._emit_headless("log.header", {"title": title}):
            return
        self._json.emit({"type": "event", "event": "header", "data": {"title": title}})

    def info(self, text: str) -> None:
        self._logger.info("%s", text)
        if self._human is not None:
            return
        if self._emit_headless("log.info", {"message": text}):
            return
        self._json.emit({"type": "log", "level": "info", "message": text})

    def warn(self, text: str) -> None:
        self._logger.warning("%s", text)
        if self._human is not None:
            return
        if self._emit_headless("log.warn", {"message": text}):
            return
        self._json.emit({"type": "log", "level": "warn", "message": text})

    def ok(self, text: str) -> None:
        self._logger.info("%s", text)
        if self._human is not None:
            return
        if self._emit_headless("log.ok", {"message": text}):
            return
        self._json.emit({"type": "log", "level": "ok", "message": text})

    def error(self, text: str) -> None:
        self._logger.error("%s", text)
        if self._human is not None:
            return
        if self._emit_headless("log.error", {"message": text}):
            return
        self._json.emit({"type": "log", "level": "error", "message": text})

    def display(self, text: str, *, level: str = "info") -> None:
        level_name = level.strip().lower()
        if level_name == "warn":
            self.warn(text)
        elif level_name == "error":
            self.error(text)
        elif level_name == "ok":
            self.ok(text)
        else:
            self.info(text)

        if self._human is not None:
            self._human.message(text)

    def show_mode(self, mode: ExecutionMode) -> None:
        self._logger.info("mode=%s", mode.value)
        if self._human is not None:
            self._human.message(f"mode={mode.value}")
            return
        if self._emit_headless("session.mode", {"mode": mode.value}):
            return
        self._json.emit({"type": "event", "event": "mode", "data": {"mode": mode.value}})

    def show_plan(self, plan: Any) -> None:
        self._logger.info("plan preview: %s", getattr(plan, "plan_description", ""))
        if self._human is not None:
            self._human.show_plan(plan)
            return
        payload: dict[str, Any] = {"plan_description": getattr(plan, "plan_description", "")}
        steps = []
        for step in getattr(plan, "steps", []):
            steps.append(
                {
                    "description": getattr(step, "description", ""),
                    "capability_id": getattr(step, "capability_id", ""),
                    "params": getattr(step, "params", {}),
                }
            )
        payload["steps"] = steps
        if self._emit_headless("plan.preview", payload):
            return
        self._json.emit({"type": "event", "event": "plan_preview", "data": payload})

    def emit_data(self, payload: Any) -> None:
        self._logger.info("result=%s", json.dumps(_serialize(payload), ensure_ascii=False))
        if self._human is not None:
            print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
            return
        if self._emit_headless("result", payload):
            return
        self._json.emit({"type": "result", "data": payload})

    def emit_event(self, event: str, payload: Any) -> None:
        self._logger.info("event=%s payload=%s", event, json.dumps(_serialize(payload), ensure_ascii=False))
        if self._human is not None:
            return
        if self._emit_headless(event, payload):
            return
        self._json.emit({"type": "event", "event": event, "data": payload})


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if dataclasses.is_dataclass(value):
        return _serialize(dataclasses.asdict(value))
    return str(value)


def _load_script_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def _load_script_lines_with_handling(path: Path, *, output: OutputFacade) -> list[str] | None:
    try:
        return _load_script_lines(path)
    except OSError as exc:
        output.display(f"failed to load script file: {exc}", level="error")
        return None


def _is_execution_running(state: CLISessionState) -> bool:
    task = state.active_execution_task
    return task is not None and not task.done()


class _ControlStdinReader:
    """Read control frames without pinning the asyncio default executor.

    A daemon thread is used here because cancellation cannot interrupt a
    blocking `stdin.readline()` call. Leaving the read inside `to_thread()`
    can keep the loop waiting on default-executor shutdown even after the
    control task itself has been cancelled.
    """

    def __init__(self, *, stdin: Any | None = None) -> None:
        self._stdin = sys.stdin if stdin is None else stdin
        self._closed = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[str | None] | None = None
        self._thread: threading.Thread | None = None

    def _ensure_started(self) -> None:
        if self._thread is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self._thread = threading.Thread(
            target=self._pump_lines,
            name="dare-control-stdin",
            daemon=True,
        )
        self._thread.start()

    def _publish(self, line: str | None) -> None:
        loop = self._loop
        queue = self._queue
        if loop is None or queue is None or loop.is_closed():
            return
        with contextlib.suppress(RuntimeError):
            loop.call_soon_threadsafe(queue.put_nowait, line)

    def _pump_lines(self) -> None:
        while True:
            raw = self._stdin.readline()
            if self._closed:
                return
            if raw == "":
                self._publish(None)
                return
            self._publish(raw.rstrip("\n"))

    async def read_line(self) -> str | None:
        self._ensure_started()
        assert self._queue is not None
        return await self._queue.get()

    def close(self) -> None:
        self._closed = True


_control_stdin_reader: _ControlStdinReader | None = None


def _get_control_stdin_reader() -> _ControlStdinReader:
    global _control_stdin_reader
    if _control_stdin_reader is None:
        _control_stdin_reader = _ControlStdinReader()
    return _control_stdin_reader


def _close_control_stdin_reader() -> None:
    global _control_stdin_reader
    if _control_stdin_reader is None:
        return
    _control_stdin_reader.close()
    _control_stdin_reader = None


async def _read_control_stdin_line() -> str | None:
    """Read one control frame line from stdin without pinning loop shutdown."""
    return await _get_control_stdin_reader().read_line()


_HOST_CONTROL_ACTIONS: tuple[ResourceAction, ...] = (
    ResourceAction.APPROVALS_LIST,
    ResourceAction.APPROVALS_POLL,
    ResourceAction.APPROVALS_GRANT,
    ResourceAction.APPROVALS_DENY,
    ResourceAction.APPROVALS_REVOKE,
    ResourceAction.MCP_LIST,
    ResourceAction.MCP_RELOAD,
    ResourceAction.MCP_SHOW_TOOL,
    ResourceAction.SKILLS_LIST,
    ResourceAction.GUIDE_INJECT,
    ResourceAction.GUIDE_LIST,
    ResourceAction.GUIDE_CLEAR,
)
_SESSION_RESUME_ACTION = "session:resume"


def _list_session_payload(*, session_store: ClientSessionStore) -> dict[str, Any]:
    """Return structured resumable-session summaries for the current workspace."""
    return {
        "sessions": [item.to_dict() for item in session_store.list_sessions()],
    }


def _control_surface_actions() -> list[str]:
    """Return the current CLI host-protocol action surface."""
    actions = {action.value for action in _HOST_CONTROL_ACTIONS}
    actions.update({"actions:list", "status:get", _SESSION_RESUME_ACTION})
    return sorted(actions)


def _status_snapshot(state: CLISessionState) -> dict[str, Any]:
    """Project CLI session state into a stable host-control snapshot."""
    running = state.status == SessionStatus.RUNNING or _is_execution_running(state)
    return {
        "mode": state.mode.value,
        "status": state.status.value,
        "running": running,
        "active_task": state.active_execution_description,
        "pending_approvals": sorted(state.pending_runtime_approvals),
    }


def _resume_target_from_control_params(*, params: dict[str, Any]) -> str:
    """Extract and normalize `session:resume` control parameters."""
    raw_target = params.get("session_id")
    if raw_target is None:
        raw_target = params.get("resume")
    target = str(raw_target).strip() if raw_target is not None else ""
    if not target:
        raise ActionClientError(
            code="INVALID_CONTROL_PARAMS",
            reason="session:resume requires params.session_id",
            target=_SESSION_RESUME_ACTION,
        )
    return target


def _resume_session_via_control(
    *,
    params: dict[str, Any],
    state: CLISessionState,
    runtime: Any,
    session_store: ClientSessionStore | None,
) -> dict[str, Any]:
    """Apply session snapshot restore through the host control surface."""
    if session_store is None:
        raise ActionClientError(
            code="SESSION_STORE_UNAVAILABLE",
            reason="session snapshot store is unavailable",
            target=_SESSION_RESUME_ACTION,
        )
    if state.status == SessionStatus.RUNNING or _is_execution_running(state):
        raise ActionClientError(
            code="INVALID_SESSION_STATE",
            reason="session:resume requires idle session state",
            target=_SESSION_RESUME_ACTION,
        )

    target = _resume_target_from_control_params(params=params)
    previous_session_id = state.conversation_id
    try:
        snapshot = session_store.load(target)
        restored_messages = _restore_session_snapshot(runtime=runtime, snapshot=snapshot)
    except (SessionStoreError, RuntimeError) as exc:
        raise ActionClientError(
            code="SESSION_RESUME_FAILED",
            reason=str(exc),
            target=_SESSION_RESUME_ACTION,
        ) from exc

    state.mode = snapshot.mode
    state.conversation_id = snapshot.session_id
    state.status = SessionStatus.IDLE
    state.active_execution_task = None
    state.active_execution_description = None
    state.clear_pending()
    state.clear_runtime_approvals()

    return {
        "requested": target,
        "session_id": snapshot.session_id,
        "previous_session_id": previous_session_id,
        "mode": snapshot.mode.value,
        "restored_messages": restored_messages,
    }


async def _dispatch_control_action(
    *,
    action_id: str,
    params: dict[str, Any],
    state: CLISessionState,
    runtime: Any,
    action_client: TransportActionClient,
    session_store: ClientSessionStore | None,
) -> Any:
    """Bridge host control actions onto the current CLI/runtime surface."""
    if action_id == ResourceAction.ACTIONS_LIST.value:
        return {"actions": _control_surface_actions()}
    if action_id == "status:get":
        return _status_snapshot(state)
    if action_id == _SESSION_RESUME_ACTION:
        return _resume_session_via_control(
            params=params,
            state=state,
            runtime=runtime,
            session_store=session_store,
        )
    resolved = ResourceAction.value_of(action_id)
    if resolved in _HOST_CONTROL_ACTIONS:
        return await action_client.invoke_action(resolved, **params)
    _ = runtime
    raise ActionClientError(
        code="UNSUPPORTED_ACTION",
        reason=f"unsupported control action: {action_id}",
        target=action_id,
    )


async def _run_control_stdin_loop(
    *,
    state: CLISessionState,
    runtime: Any,
    action_client: TransportActionClient,
    session_store: ClientSessionStore | None,
    output: OutputFacade | None = None,
) -> None:
    """Process structured host control commands from stdin."""
    renderer = ControlStdinRenderer()
    try:
        while True:
            line = await _read_control_stdin_line()
            if line is None:
                return
            if not line.strip():
                continue

            request_id = "?"
            action_id = "?"
            try:
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError("control frame must be a JSON object")
                request_id = str(payload.get("id", "?")).strip() or "?"
                schema_version = str(payload.get("schema_version", "")).strip()
                if schema_version != ControlStdinRenderer.schema_version:
                    raise ValueError(
                        "unsupported control schema_version: "
                        f"{schema_version or '<missing>'}"
                    )
                action_id = str(payload.get("action", "")).strip()
                if not action_id:
                    raise ValueError("control action is required")
                params = payload.get("params", {})
                if params is None:
                    params = {}
                if not isinstance(params, dict):
                    raise ValueError("control params must be a JSON object")
                result = await _dispatch_control_action(
                    action_id=action_id,
                    params=params,
                    state=state,
                    runtime=runtime,
                    action_client=action_client,
                    session_store=session_store,
                )
                if action_id == _SESSION_RESUME_ACTION and output is not None:
                    resumed_session_id = state.conversation_id
                    if isinstance(result, dict):
                        resumed_session_id = str(result.get("session_id", resumed_session_id))
                    output.set_protocol_context(
                        session_id=resumed_session_id,
                        run_id=resumed_session_id,
                    )
            except json.JSONDecodeError as exc:
                renderer.emit(
                    request_id=request_id,
                    ok=False,
                    error={"code": "INVALID_JSON", "message": str(exc), "target": "control-stdin"},
                )
                continue
            except ActionClientError as exc:
                renderer.emit(
                    request_id=request_id,
                    ok=False,
                    error={"code": exc.code, "message": exc.reason, "target": exc.target},
                )
                continue
            except Exception as exc:  # noqa: BLE001
                renderer.emit(
                    request_id=request_id,
                    ok=False,
                    error={"code": "INVALID_CONTROL_FRAME", "message": str(exc), "target": action_id},
                )
                continue

            renderer.emit(request_id=request_id, ok=True, result=_serialize(result), error=None)
    finally:
        _close_control_stdin_reader()


async def _execute_task_and_report(
    *,
    runtime: Any,
    output: OutputFacade,
    state: CLISessionState,
    task_text: str,
) -> bool:
    if output.is_headless:
        output.emit_event("task.started", {"task": task_text, "mode": state.mode.value})
    try:
        result = await run_task(
            agent=runtime.agent,
            task_text=task_text,
            conversation_id=state.conversation_id,
            transport=runtime.channel,
        )
    except asyncio.CancelledError:
        state.last_execution_success = False
        state.execution_failures += 1
        if output.is_headless:
            payload = state.headless_failure_payload or {"task": task_text, "error": "execution cancelled"}
            state.headless_failure_payload = None
            output.emit_event("task.failed", payload)
            return False
        output.display("execution cancelled", level="warn")
        return False
    except Exception as exc:  # noqa: BLE001
        state.last_execution_success = False
        state.execution_failures += 1
        if output.is_headless:
            output.emit_event("task.failed", {"task": task_text, "error": str(exc)})
            return False
        output.display(f"execution error: {exc}", level="error")
        return False

    if result.success:
        state.last_execution_success = True
        text = format_run_output(result.output)
        if output.is_headless:
            output.emit_event(
                "task.completed",
                {
                    "task": task_text,
                    "output": _serialize(result.output),
                    "rendered_output": text,
                },
            )
            return True
        if text:
            output.display(text)
        else:
            output.display("task completed", level="ok")
        output.ok("task completed")
        return True

    state.last_execution_success = False
    state.execution_failures += 1
    if output.is_headless:
        output.emit_event(
            "task.failed",
            {
                "task": task_text,
                "errors": _serialize(result.errors),
                "output": _serialize(getattr(result, "output", None)),
            },
        )
        return False
    output.display("task failed", level="error")
    if result.errors:
        output.display(f"errors: {result.errors}", level="error")
    return False


async def _finalize_background_task_if_done(
    state: CLISessionState,
    *,
    output: OutputFacade,
) -> None:
    task = state.active_execution_task
    if task is None or not task.done():
        return
    try:
        await task
    except asyncio.CancelledError:
        output.display("execution cancelled", level="warn")
    except Exception as exc:  # noqa: BLE001
        output.display(f"execution failed: {exc}", level="error")
    finally:
        state.active_execution_task = None
        state.active_execution_description = None
        state.clear_runtime_approvals()
        if state.status == SessionStatus.RUNNING:
            state.status = SessionStatus.IDLE


async def _wait_for_background_task(
    state: CLISessionState,
    *,
    output: OutputFacade,
) -> None:
    """Wait for active background task completion before final state evaluation."""
    task = state.active_execution_task
    if task is not None and not task.done():
        # Ensure scripted/non-interactive flows can rely on deterministic exit codes.
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
    await _finalize_background_task_if_done(state, output=output)


async def _wait_until_prompt_allowed(
    state: CLISessionState,
    *,
    output: OutputFacade,
    release_on_pending: bool = True,
    poll_interval_seconds: float = 0.05,
) -> None:
    """Hold the prompt while a task is running unless user action is required."""
    while _is_execution_running(state):
        if release_on_pending and state.has_pending_runtime_approval():
            return
        await asyncio.sleep(poll_interval_seconds)
        await _finalize_background_task_if_done(state, output=output)
    await _finalize_background_task_if_done(state, output=output)


def _normalize_mode(value: str) -> ExecutionMode:
    return ExecutionMode.PLAN if value == "plan" else ExecutionMode.EXECUTE


def _resolve_resume_target(
    *,
    resume: str | None,
    session_id: str | None,
) -> str | None:
    """Normalize resume inputs from CLI flags and enforce deterministic conflicts."""
    resume_target = resume.strip() if isinstance(resume, str) else None
    session_target = session_id.strip() if isinstance(session_id, str) else None
    if resume_target == "":
        resume_target = None
    if session_target == "":
        session_target = None
    if (
        resume_target is not None
        and session_target is not None
        and resume_target != session_target
    ):
        raise ValueError(
            "cannot use --resume and --session-id with different targets; pass one target or matching values"
        )
    return session_target or resume_target


@dataclasses.dataclass(frozen=True)
class _ResumeMetadata:
    """Normalized resume details emitted to logs/headless envelopes."""

    requested: str
    session_id: str
    restored_messages: int


def _runtime_session_context(runtime: Any) -> Any | None:
    agent = getattr(runtime, "agent", None)
    return getattr(agent, "context", None)


def _restore_session_snapshot(*, runtime: Any, snapshot: SessionSnapshot) -> int:
    """Restore persisted STM history into a freshly bootstrapped runtime."""
    context = _runtime_session_context(runtime)
    if context is None:
        raise RuntimeError("runtime agent context is unavailable for session resume")
    clear = getattr(context, "stm_clear", None)
    add = getattr(context, "stm_add", None)
    if not callable(clear) or not callable(add):
        raise RuntimeError("runtime agent context does not support session resume")
    clear()
    for message in snapshot.messages:
        add(message)
    return len(snapshot.messages)


def _snapshot_messages_for_persistence(runtime: Any) -> list[Any] | None:
    """Best-effort access to runtime STM for session snapshot writes."""
    context = _runtime_session_context(runtime)
    get_messages = getattr(context, "stm_get", None) if context is not None else None
    if not callable(get_messages):
        return None
    messages = get_messages()
    return list(messages) if isinstance(messages, list) else list(messages)


def _build_session_state(
    *,
    mode: str,
    resume: str | None,
    runtime: Any,
    session_store: ClientSessionStore | None,
) -> tuple[CLISessionState, _ResumeMetadata | None]:
    """Create a fresh CLI state or restore one from a persisted snapshot."""
    if session_store is None or not isinstance(resume, str):
        return CLISessionState(mode=_normalize_mode(mode)), None
    snapshot = session_store.load(resume)
    restored_messages = _restore_session_snapshot(runtime=runtime, snapshot=snapshot)
    state = CLISessionState(
        mode=snapshot.mode,
        conversation_id=snapshot.session_id,
    )
    return state, _ResumeMetadata(
        requested=resume.strip() or "latest",
        session_id=snapshot.session_id,
        restored_messages=restored_messages,
    )


def _persist_session_snapshot(
    *,
    runtime: Any,
    state: CLISessionState,
    session_store: ClientSessionStore | None,
) -> None:
    """Persist current runtime STM into the workspace session store."""
    if session_store is None:
        return
    messages = _snapshot_messages_for_persistence(runtime)
    if messages is None:
        return
    session_store.save(state=state, messages=messages)


@dataclasses.dataclass
class _ApprovalWatchState:
    """Track the currently pending approval request for timeout enforcement."""

    request_id: str | None = None
    pending_since_monotonic: float | None = None

    def reset(self) -> None:
        """Drop pending approval timing state before/after each foreground task."""
        self.request_id = None
        self.pending_since_monotonic = None

    def mark_pending(self, request_id: str) -> None:
        normalized = request_id.strip() if request_id.strip() else "?"
        if self.request_id == normalized and self.pending_since_monotonic is not None:
            return
        self.request_id = normalized
        self.pending_since_monotonic = time.monotonic()

    def mark_resolved(self, request_id: str) -> None:
        if self.request_id is None:
            return
        normalized = request_id.strip() if request_id.strip() else "?"
        if normalized not in {"?", self.request_id}:
            return
        self.request_id = None
        self.pending_since_monotonic = None


DEFAULT_AUTO_APPROVE_TOOLS: frozenset[str] = frozenset(
    {
        # Low-risk built-in tools; callers can extend with --auto-approve-tool.
        # Keep this set aligned with currently registered runtime tool names.
        "read_file",
        "search_code",
    }
)


def _approval_request_lines(
    *,
    request: dict[str, Any],
    tool_name: str,
    capability_id: str,
) -> list[str]:
    """Render the approval request so the user can see exactly what is being allowed."""
    params = request.get("params", {})
    command = request.get("command")
    reason = request.get("reason")
    cwd = params.get("cwd") if isinstance(params, dict) else None

    if capability_id == "run_command" or tool_name == "run_command":
        lines = ["Agent wants to run a shell command."]
    else:
        label = tool_name or capability_id or "Tool"
        lines = [f"{label} requires approval."]

    if isinstance(reason, str) and reason.strip():
        lines.append(f"Reason: {reason.strip()}")
    if isinstance(command, str) and command.strip():
        lines.append(f"Command: {command.strip()}")
    if isinstance(cwd, str) and cwd.strip():
        lines.append(f"Cwd: {cwd.strip()}")
    has_command = isinstance(command, str) and bool(command.strip())
    if not has_command and isinstance(params, dict) and params:
        lines.append(f"Params: {json.dumps(_serialize(params), ensure_ascii=False, sort_keys=True)}")

    lines.extend(
        [
            "Choose what to do:",
            "1. Allow once",
            "2. Always allow this exact command in this session",
            "3. Deny (default)",
        ]
    )
    return lines


def _parse_inline_approval_choice(raw: str) -> tuple[ResourceAction, str, str] | None:
    """Interpret interactive approval input."""
    answer = raw.strip().lower()
    if answer in {"1", "y", "yes"}:
        return ResourceAction.APPROVALS_GRANT, "once", "exact_params"
    if answer in {"2", "a", "always", "session"}:
        return ResourceAction.APPROVALS_GRANT, "session", "exact_params"
    if answer in {"", "3", "n", "no"}:
        return ResourceAction.APPROVALS_DENY, "once", "exact_params"
    return None


async def _resolve_inline_chat_approval(
    *,
    action_client: TransportActionClient,
    output: OutputFacade,
    request: dict[str, Any],
    tool_name: str,
    capability_id: str,
) -> None:
    """Collect an inline approval decision for human chat sessions."""
    normalized_request = str(request.get("request_id", "?")).strip() or "?"
    for line in _approval_request_lines(
        request=request,
        tool_name=tool_name.strip(),
        capability_id=capability_id.strip(),
    ):
        output.display(line, level="warn")

    while True:
        try:
            raw = await asyncio.to_thread(input, "approve> ")
        except (EOFError, KeyboardInterrupt):
            raw = ""
        parsed = _parse_inline_approval_choice(raw)

        if parsed is None:
            output.display("Choose 1, 2, or 3.", level="warn")
            continue
        action, scope, matcher = parsed
        decision = "allow" if action == ResourceAction.APPROVALS_GRANT else "deny"

        try:
            await action_client.invoke_action(
                action,
                request_id=normalized_request,
                scope=scope,
                matcher=matcher,
            )
        except Exception as exc:  # noqa: BLE001
            output.display(f"failed to submit approval decision: {exc}", level="error")
            continue

        if action == ResourceAction.APPROVALS_GRANT and scope == "session":
            output.display(
                "Same command will be auto-approved for the rest of this session.",
                level="ok",
            )
        output.info(
            "approval decision submitted: "
            f"request_id={normalized_request}, decision={decision}, scope={scope}, matcher={matcher}"
        )
        return


@dataclasses.dataclass
class _RunApprovalPolicy:
    """Auto-approval policy used by `run` mode transport event handling."""

    action_client: TransportActionClient
    output: OutputFacade
    watch: _ApprovalWatchState
    auto_approve_tools: set[str]
    auto_approve_all: bool = False
    seen_disallowed: set[str] = dataclasses.field(default_factory=set)
    attempted: set[str] = dataclasses.field(default_factory=set)

    async def on_pending(self, request_id: str, tool_name: str, capability_id: str) -> None:
        normalized_request = request_id.strip() if request_id.strip() else "?"
        normalized_tool = tool_name.strip() if tool_name.strip() else "?"
        self.watch.mark_pending(normalized_request)
        if not self.auto_approve_all and not self.auto_approve_tools:
            return

        if not self.auto_approve_all and normalized_tool not in self.auto_approve_tools:
            if normalized_request in self.seen_disallowed:
                return
            self.seen_disallowed.add(normalized_request)
            self.output.display(
                "auto-approve skipped: "
                f"request_id={normalized_request}, tool={normalized_tool}, capability={capability_id}",
                level="warn",
            )
            self.output.display(
                "rerun with `--auto-approve-tool "
                f"{normalized_tool}` to allow this tool in run mode",
                level="warn",
            )
            return

        if normalized_request in self.attempted:
            return
        self.attempted.add(normalized_request)
        self.output.info(
            f"auto-approving request_id={normalized_request} for tool={normalized_tool}"
        )
        try:
            await self.action_client.invoke_action(
                ResourceAction.APPROVALS_GRANT,
                request_id=normalized_request,
                scope="once",
                matcher="exact_params",
            )
        except Exception as exc:  # noqa: BLE001
            self.output.display(
                f"auto-approve failed for request_id={normalized_request}: {exc}"
                ,
                level="error",
            )
            return
        self.output.ok(f"auto-approved request_id={normalized_request}")
        # Clear timeout watch immediately after grant acknowledgement.
        self.watch.mark_resolved(normalized_request)


async def _execute_task_with_approval_timeout(
    *,
    runtime: Any,
    output: OutputFacade,
    state: CLISessionState,
    task_text: str,
    approval_watch: _ApprovalWatchState,
    approval_timeout_seconds: float | None,
) -> bool:
    """Run one task and fail fast when approval waits exceed the configured budget."""
    # Approval timeout is scoped to a single task execution. Reset any stale
    # pending approval timestamp from a previous scripted line before starting.
    approval_watch.reset()
    task = asyncio.create_task(
        _execute_task_and_report(
            runtime=runtime,
            output=output,
            state=state,
            task_text=task_text,
        )
    )
    try:
        while not task.done():
            if (
                approval_timeout_seconds is not None
                and approval_timeout_seconds > 0
                and approval_watch.pending_since_monotonic is not None
            ):
                elapsed = time.monotonic() - approval_watch.pending_since_monotonic
                if elapsed >= approval_timeout_seconds:
                    request_id = approval_watch.request_id or "?"
                    if output.is_headless:
                        state.headless_failure_payload = {
                            "task": task_text,
                            "request_id": request_id,
                            "timeout_seconds": approval_timeout_seconds,
                            "error": (
                                "approval wait timed out "
                                f"(request_id={request_id}, timeout={approval_timeout_seconds:.1f}s)"
                            ),
                        }
                    else:
                        output.display(
                            "approval wait timed out "
                            f"(request_id={request_id}, timeout={approval_timeout_seconds:.1f}s)",
                            level="error",
                        )
                        output.display(
                            "rerun with `--auto-approve-tool <tool_name>` "
                            "or use `chat` mode to approve manually",
                            level="error",
                        )
                    task.cancel()
                    break
            await asyncio.sleep(0.1)

        try:
            return await task
        except asyncio.CancelledError:
            return False
    finally:
        approval_watch.reset()
        state.clear_runtime_approvals()
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


async def _handle_shell_command(
    command: Command,
    *,
    state: CLISessionState,
    runtime: Any,
    action_client: TransportActionClient,
    output: OutputFacade,
    background_execute: bool,
    session_store: ClientSessionStore | None = None,
    approval_watch: _ApprovalWatchState | None = None,
    approval_timeout_seconds: float | None = None,
) -> bool:
    if command.type == CommandType.QUIT:
        if _is_execution_running(state):
            output.display("cancelling running execution", level="warn")
            assert state.active_execution_task is not None
            state.active_execution_task.cancel()
            await _finalize_background_task_if_done(state, output=output)
        output.display("bye")
        return True

    if command.type == CommandType.HELP:
        output.display(
            "/mode [plan|execute], /approve, /reject, /status, "
            "/approvals [...], /mcp [...], /tools list, /sessions list, /skills list, "
            "/config show, /model show, /interrupt, /quit"
        )
        return False

    if command.type == CommandType.STATUS:
        running = _is_execution_running(state)
        output.display(f"status={state.status.value}, mode={state.mode.value}, running={running}")
        if running and state.active_execution_description:
            output.display(f"active_task={state.active_execution_description}")
        return False

    if command.type == CommandType.MODE:
        if not command.args:
            output.display("/mode requires plan or execute", level="warn")
            return False
        mode = command.args[0].strip().lower()
        if mode not in {"plan", "execute"}:
            output.display(f"unknown mode: {mode}", level="warn")
            return False
        state.mode = _normalize_mode(mode)
        output.show_mode(state.mode)
        return False

    if command.type == CommandType.APPROVE:
        if state.pending_task_description is None:
            output.display("no pending plan", level="warn")
            return False
        task_text = state.pending_task_description
        if background_execute and _is_execution_running(state):
            output.display("another execution is running", level="warn")
            return False
        state.clear_pending()
        if background_execute:
            state.status = SessionStatus.RUNNING
            state.active_execution_description = task_text
            state.active_execution_task = asyncio.create_task(
                _execute_task_and_report(
                    runtime=runtime,
                    output=output,
                    state=state,
                    task_text=task_text,
                )
            )
            output.info("execution started in background")
            return False

        state.status = SessionStatus.RUNNING
        state.active_execution_description = task_text
        try:
            if approval_watch is not None:
                await _execute_task_with_approval_timeout(
                    runtime=runtime,
                    output=output,
                    state=state,
                    task_text=task_text,
                    approval_watch=approval_watch,
                    approval_timeout_seconds=approval_timeout_seconds,
                )
            else:
                await _execute_task_and_report(
                    runtime=runtime,
                    output=output,
                    state=state,
                    task_text=task_text,
                )
        finally:
            state.active_execution_description = None
        state.status = SessionStatus.IDLE
        return False

    if command.type == CommandType.REJECT:
        state.clear_pending()
        if not _is_execution_running(state):
            state.status = SessionStatus.IDLE
        output.display("plan rejected")
        return False

    if command.type == CommandType.APPROVALS:
        try:
            payload = await handle_approvals_tokens(command.args, action_client=action_client)
        except Exception as exc:  # noqa: BLE001
            output.display(str(exc), level="error")
            for line in approvals_usage_lines():
                output.display(line)
            return False
        output.emit_data(_serialize(payload))
        return False

    if command.type == CommandType.MCP:
        try:
            payload = await handle_mcp_tokens(command.args, runtime=runtime)
        except Exception as exc:  # noqa: BLE001
            output.display(str(exc), level="error")
            output.display("/mcp list|inspect [tool_name]|reload [paths...]|unload")
            return False
        if "tools" in payload:
            output.display(format_mcp_inspection(payload["tools"]))
        else:
            output.emit_data(_serialize(payload))
        return False

    if command.type == CommandType.TOOLS:
        payload = await list_tools(action_client=action_client)
        output.emit_data(_serialize(payload))
        return False

    if command.type == CommandType.SESSIONS:
        if command.args[:1] not in ([], ["list"]):
            output.display("/sessions list", level="warn")
            return False
        if session_store is None:
            output.display("session store unavailable", level="error")
            return False
        output.emit_data(_serialize(_list_session_payload(session_store=session_store)))
        return False

    if command.type == CommandType.SKILLS:
        payload = await list_skills(action_client=action_client)
        output.emit_data(_serialize(payload))
        return False

    if command.type == CommandType.CONFIG:
        payload = await show_config(action_client=action_client)
        output.emit_data(_serialize(payload))
        return False

    if command.type == CommandType.MODEL:
        payload = await show_model(action_client=action_client)
        output.emit_data(_serialize(payload))
        return False

    if command.type == CommandType.INTERRUPT:
        if _is_execution_running(state):
            assert state.active_execution_task is not None
            state.active_execution_task.cancel()
            await _finalize_background_task_if_done(state, output=output)
            return False
        payload = await send_control("interrupt", action_client=action_client)
        output.emit_data(_serialize(payload))
        return False

    return False


async def _run_cli_loop(
    lines: Iterable[str],
    *,
    state: CLISessionState,
    runtime: Any,
    action_client: TransportActionClient,
    output: OutputFacade,
    background_execute: bool,
    session_store: ClientSessionStore | None = None,
    approval_watch: _ApprovalWatchState | None = None,
    approval_timeout_seconds: float | None = None,
) -> bool:
    quit_requested = False
    for raw in lines:
        await _finalize_background_task_if_done(state, output=output)

        parsed = parse_command(raw)
        if isinstance(parsed, Command):
            try:
                quit_requested = await _handle_shell_command(
                    parsed,
                    state=state,
                    runtime=runtime,
                    action_client=action_client,
                    output=output,
                    background_execute=background_execute,
                    session_store=session_store,
                    approval_watch=approval_watch,
                    approval_timeout_seconds=approval_timeout_seconds,
                )
            except ActionClientError as exc:
                # Command failures must affect scripted exit status.
                state.last_execution_success = False
                state.execution_failures += 1
                output.display(str(exc), level="error")
                continue
            except Exception as exc:  # noqa: BLE001
                # Keep command exceptions visible while preserving deterministic script rc.
                state.last_execution_success = False
                state.execution_failures += 1
                output.display(f"command failed: {exc}", level="error")
                continue
            if quit_requested:
                break
            continue

        _none, task_text = parsed
        if not task_text:
            continue

        if state.mode == ExecutionMode.PLAN:
            state.pending_task_description = task_text
            try:
                state.pending_plan = await preview_plan(
                    task_text=task_text,
                    model=runtime.model,
                    workspace_dir=runtime.config.workspace_dir,
                    user_dir=runtime.config.user_dir,
                )
            except Exception as exc:  # noqa: BLE001
                state.clear_pending()
                # Plan preview failures should affect scripted exit status.
                state.last_execution_success = False
                state.execution_failures += 1
                output.display(f"plan preview failed: {exc}", level="error")
                continue
            state.status = SessionStatus.AWAITING_APPROVAL
            output.show_plan(state.pending_plan)
            output.display("type /approve to execute or /reject to cancel")
            continue

        if background_execute:
            if _is_execution_running(state):
                output.display("another execution is running", level="warn")
                continue
            state.status = SessionStatus.RUNNING
            state.active_execution_description = task_text
            state.active_execution_task = asyncio.create_task(
                _execute_task_and_report(
                    runtime=runtime,
                    output=output,
                    state=state,
                    task_text=task_text,
                )
            )
            output.info("execution started in background")
            continue

        state.status = SessionStatus.RUNNING
        state.active_execution_description = task_text
        try:
            if approval_watch is not None:
                await _execute_task_with_approval_timeout(
                    runtime=runtime,
                    output=output,
                    state=state,
                    task_text=task_text,
                    approval_watch=approval_watch,
                    approval_timeout_seconds=approval_timeout_seconds,
                )
            else:
                await _execute_task_and_report(
                    runtime=runtime,
                    output=output,
                    state=state,
                    task_text=task_text,
                )
        finally:
            state.active_execution_description = None
        state.status = SessionStatus.IDLE

    await _finalize_background_task_if_done(state, output=output)
    return quit_requested


def _on_transport_event(
    payload: dict[str, Any],
    *,
    output: OutputFacade,
    on_approval_pending: Callable[[dict[str, Any], str, str], Awaitable[None] | None] | None = None,
    on_approval_resolved: Callable[[str], Awaitable[None] | None] | None = None,
    suppress_human_approval_pending_output: bool = False,
) -> Awaitable[None] | None:
    return _on_transport_event_async(
        payload,
        output=output,
        on_approval_pending=on_approval_pending,
        on_approval_resolved=on_approval_resolved,
        suppress_human_approval_pending_output=suppress_human_approval_pending_output,
    )


async def _on_transport_event_async(
    payload: dict[str, Any],
    *,
    output: OutputFacade,
    on_approval_pending: Callable[[dict[str, Any], str, str], Awaitable[None] | None] | None = None,
    on_approval_resolved: Callable[[str], Awaitable[None] | None] | None = None,
    suppress_human_approval_pending_output: bool = False,
) -> None:
    select_kind = payload.get("select_kind")
    select_domain = payload.get("select_domain")
    if select_domain == "approval" and select_kind == "ask":
        metadata = payload.get("metadata", {})
        request = metadata.get("request", {}) if isinstance(metadata, dict) else {}
        request_id = str(request.get("request_id", payload.get("id", "?")))
        capability_id = str(metadata.get("capability_id", "?")) if isinstance(metadata, dict) else "?"
        tool_name = str(metadata.get("tool_name", "?")) if isinstance(metadata, dict) else "?"
        if on_approval_pending is not None:
            maybe_awaitable = on_approval_pending(request, tool_name, capability_id)
            if maybe_awaitable is not None:
                await maybe_awaitable
        if output.is_headless:
            output.emit_event(
                "approval.pending",
                {
                    "request_id": request_id,
                    "capability_id": capability_id,
                    "tool_name": tool_name,
                    "request": request,
                },
            )
            return
        message = f"approval pending: request_id={request_id}, capability={capability_id}"
        if suppress_human_approval_pending_output and output.mode == "human":
            output.warn(message)
        else:
            output.display(message, level="warn")
        return
    if select_domain == "approval" and select_kind == "answered":
        selected = payload.get("selected", {})
        request_id = str(selected.get("request_id", payload.get("id", "?"))) if isinstance(selected, dict) else "?"
        decision = selected.get("decision", "?") if isinstance(selected, dict) else "?"
        if on_approval_resolved is not None:
            maybe_awaitable = on_approval_resolved(request_id)
            if maybe_awaitable is not None:
                await maybe_awaitable
        if output.is_headless:
            output.emit_event(
                "approval.resolved",
                {"request_id": request_id, "decision": decision},
            )
            return
        output.info(f"approval resolved: request_id={request_id}, decision={decision}")
        return
    message_kind = payload.get("message_kind")
    data = payload.get("data", {})
    if message_kind == "summary" and isinstance(data, dict) and data.get("source") == "hook":
        hook_phase = str(data.get("phase", "")).strip()
        hook_payload = data.get("payload", {})
        if output.is_headless and isinstance(hook_payload, dict):
            if hook_phase == "before_tool":
                output.emit_event("tool.invoke", hook_payload)
                return
            if hook_phase == "after_tool":
                event_name = "tool.result" if hook_payload.get("success") else "tool.error"
                output.emit_event(event_name, hook_payload)
                return
            if hook_phase == "after_model":
                output.emit_event("model.response", hook_payload)
                return
        output.info(f"hook event: {payload.get('text')}")
        return
    # Keep unknown payloads observable in json mode while avoiding noisy human logs.
    if output.is_headless:
        output.emit_event("transport.raw", payload)
        return
    if output.mode == "json":
        output.emit_event("transport", _serialize(payload))


async def _run_chat(
    *,
    runtime: Any,
    action_client: TransportActionClient,
    output: OutputFacade,
    mode: str,
    script_lines: list[str] | None,
    approval_timeout_seconds: float | None = None,
    control_stdin: bool = False,
    initial_state: CLISessionState | None = None,
    session_store: ClientSessionStore | None = None,
    resume_metadata: _ResumeMetadata | None = None,
) -> int:
    state = initial_state or CLISessionState(mode=_normalize_mode(mode))
    if output.is_headless:
        output.set_protocol_context(session_id=state.conversation_id, run_id=state.conversation_id)
        payload: dict[str, Any] = {
            "mode": state.mode.value,
            "entrypoint": "script",
        }
        if resume_metadata is not None:
            payload["resumed"] = True
            payload["resume_requested"] = resume_metadata.requested
            payload["restored_messages"] = resume_metadata.restored_messages
        output.emit_event("session.started", payload)
    inline_chat_approvals = script_lines is None and output.mode == "human"
    approval_watch = _ApprovalWatchState() if script_lines is not None and approval_timeout_seconds is not None else None

    async def _handle_chat_approval_pending(request: dict[str, Any], tool_name: str, capability_id: str) -> None:
        request_id = str(request.get("request_id", "?")).strip() or "?"
        state.mark_runtime_approval_pending(request_id)
        if approval_watch is not None:
            approval_watch.mark_pending(request_id)
        if not inline_chat_approvals:
            return
        await _resolve_inline_chat_approval(
            action_client=action_client,
            output=output,
            request=request,
            tool_name=tool_name,
            capability_id=capability_id,
        )

    def _handle_chat_approval_resolved(request_id: str) -> None:
        state.mark_runtime_approval_resolved(request_id)
        if approval_watch is not None:
            approval_watch.mark_resolved(request_id)

    output.info(f"mode={state.mode.value}")
    pump = EventPump(
        client_channel=runtime.client_channel,
        on_event=lambda payload: _on_transport_event(
            payload,
            output=output,
            on_approval_pending=_handle_chat_approval_pending,
            on_approval_resolved=_handle_chat_approval_resolved,
            suppress_human_approval_pending_output=inline_chat_approvals,
        ),
    )
    pump.start()
    control_task: asyncio.Task[None] | None = None
    if output.is_headless and control_stdin:
        control_task = asyncio.create_task(
            _run_control_stdin_loop(
                state=state,
                runtime=runtime,
                action_client=action_client,
                session_store=session_store,
                output=output,
            )
        )
    try:
        if script_lines is not None:
            await _run_cli_loop(
                script_lines,
                state=state,
                runtime=runtime,
                action_client=action_client,
                output=output,
                # Script mode must be deterministic: run each task line to completion
                # so later lines are not skipped behind an active background task.
                background_execute=False,
                approval_watch=approval_watch,
                approval_timeout_seconds=approval_timeout_seconds,
                session_store=session_store,
            )
            try:
                _persist_session_snapshot(runtime=runtime, state=state, session_store=session_store)
            except (OSError, SessionStoreError, RuntimeError) as exc:
                output.display(f"failed to persist session snapshot: {exc}", level="error")
                return 1
            if _is_execution_running(state):
                output.display("waiting for last background execution", level="warn")
                await _wait_for_background_task(state, output=output)
            return 0 if state.execution_failures == 0 else 1

        output.display("type /help for commands. /quit to exit.")
        while True:
            try:
                # Offload blocking stdin reads so background tasks/event pump keep running.
                raw = await asyncio.to_thread(input, "dare> ")
            except (EOFError, KeyboardInterrupt):
                print("", flush=True)
                break
            raw = raw.strip()
            if not raw:
                continue
            quit_requested = await _run_cli_loop(
                [raw],
                state=state,
                runtime=runtime,
                action_client=action_client,
                output=output,
                background_execute=True,
                session_store=session_store,
            )
            await _wait_until_prompt_allowed(
                state,
                output=output,
                release_on_pending=not inline_chat_approvals,
            )
            if not _is_execution_running(state):
                try:
                    _persist_session_snapshot(runtime=runtime, state=state, session_store=session_store)
                except (OSError, SessionStoreError, RuntimeError) as exc:
                    output.display(f"failed to persist session snapshot: {exc}", level="error")
                    return 1
            if quit_requested:
                break
        if _is_execution_running(state):
            output.display("waiting for running execution", level="warn")
            await _wait_for_background_task(state, output=output)
        return 0
    finally:
        if control_task is not None:
            control_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await control_task
        await pump.stop()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DARE external CLI")
    parser.add_argument("--workspace", default=str(Path.cwd()), help="workspace root path")
    parser.add_argument("--user-dir", default=str(Path.home()), help="user directory path")
    parser.add_argument("--adapter", default=None, help="llm adapter override (openai/openrouter/anthropic/huawei-modelarts)")
    parser.add_argument("--model", default=None, help="llm model override")
    parser.add_argument("--api-key", default=None, help="llm api key override")
    parser.add_argument("--endpoint", default=None, help="llm endpoint override")
    parser.add_argument("--max-tokens", type=int, default=None, help="max tokens override")
    parser.add_argument(
        "--system-prompt-mode",
        choices=["replace", "append"],
        default=None,
        help="runtime system prompt policy override",
    )
    parser.add_argument("--system-prompt-text", default=None, help="inline runtime system prompt override")
    parser.add_argument("--system-prompt-file", default=None, help="runtime system prompt file path override")
    parser.add_argument("--timeout", type=float, default=60.0, help="request timeout seconds")
    parser.add_argument("--mcp-path", action="append", default=None, help="extra MCP path override (repeatable)")
    parser.add_argument("--output", choices=["human", "json"], default="human")

    sub = parser.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="interactive chat mode")
    chat.add_argument("--mode", choices=["plan", "execute"], default="execute")
    chat.add_argument("--script", default=None, help="optional script file")
    chat.add_argument(
        "--resume",
        nargs="?",
        const="latest",
        default=None,
        help="resume latest or specified CLI session",
    )
    chat.add_argument(
        "--session-id",
        default=None,
        help="resume a specific CLI session by id (compat alias of --resume <session-id>)",
    )

    run = sub.add_parser("run", help="run one task and exit")
    run.add_argument("--task", required=True)
    run.add_argument("--mode", choices=["plan", "execute"], default="execute")
    run.add_argument(
        "--resume",
        nargs="?",
        const="latest",
        default=None,
        help="resume latest or specified CLI session",
    )
    run.add_argument(
        "--session-id",
        default=None,
        help="resume a specific CLI session by id (compat alias of --resume <session-id>)",
    )
    run.add_argument("--approve", action="store_true", help="execute after plan preview when mode=plan")
    run.add_argument(
        "--approval-timeout-seconds",
        type=float,
        default=120.0,
        help="when approval is pending, fail run after timeout (<=0 disables)",
    )
    run.add_argument(
        "--auto-approve",
        action="store_true",
        help="auto-grant approvals for low-risk tools in run mode",
    )
    run.add_argument(
        "--auto-approve-tool",
        action="append",
        default=None,
        help="extra tool name eligible for auto-approve (repeatable)",
    )
    run.add_argument(
        "--full-auto",
        action="store_true",
        help="fully autonomous mode: auto-approve ALL tool invocations and "
        "auto-respond to ask_user questions (no human interaction required)",
    )
    run.add_argument(
        "--headless",
        action="store_true",
        help="planned host-orchestrated headless mode for non-interactive execution",
    )
    run.add_argument(
        "--control-stdin",
        action="store_true",
        help="enable structured control commands from stdin in headless mode",
    )

    script = sub.add_parser("script", help="run script and exit")
    script.add_argument("--file", required=True)
    script.add_argument("--mode", choices=["plan", "execute"], default="execute")
    script.add_argument(
        "--resume",
        nargs="?",
        const="latest",
        default=None,
        help="resume latest or specified CLI session",
    )
    script.add_argument(
        "--session-id",
        default=None,
        help="resume a specific CLI session by id (compat alias of --resume <session-id>)",
    )
    script.add_argument(
        "--headless",
        action="store_true",
        help="planned host-orchestrated headless mode for non-interactive execution",
    )
    script.add_argument(
        "--control-stdin",
        action="store_true",
        help="enable structured control commands from stdin in headless mode",
    )
    script.add_argument(
        "--approval-timeout-seconds",
        type=float,
        default=None,
        help="when approval is pending in script mode, fail after timeout seconds (<=0 disables)",
    )

    approvals = sub.add_parser("approvals", help="approval controls")
    approvals_sub = approvals.add_subparsers(dest="approvals_cmd", required=True)
    approvals_sub.add_parser("list")
    poll = approvals_sub.add_parser("poll")
    poll.add_argument("--timeout-ms", default=None)
    poll.add_argument("--timeout-seconds", default=None)
    grant = approvals_sub.add_parser("grant")
    grant.add_argument("request_id")
    grant.add_argument("--scope", default="workspace")
    grant.add_argument("--matcher", default="exact_params")
    grant.add_argument("--matcher-value", default=None)
    grant.add_argument("--session-id", default=None, help="optional request session_id scope")
    deny = approvals_sub.add_parser("deny")
    deny.add_argument("request_id")
    deny.add_argument("--scope", default="once")
    deny.add_argument("--matcher", default="exact_params")
    deny.add_argument("--matcher-value", default=None)
    deny.add_argument("--session-id", default=None, help="optional request session_id scope")
    revoke = approvals_sub.add_parser("revoke")
    revoke.add_argument("rule_id")

    mcp = sub.add_parser("mcp", help="mcp controls")
    mcp_sub = mcp.add_subparsers(dest="mcp_cmd", required=True)
    mcp_sub.add_parser("list")
    inspect = mcp_sub.add_parser("inspect")
    inspect.add_argument("tool_name", nargs="?")
    reload_cmd = mcp_sub.add_parser("reload")
    reload_cmd.add_argument("paths", nargs="*")
    mcp_sub.add_parser("unload")

    tools = sub.add_parser("tools", help="list tools")
    tools_sub = tools.add_subparsers(dest="tools_cmd", required=True)
    tools_sub.add_parser("list")

    sessions = sub.add_parser("sessions", help="list resumable sessions")
    sessions_sub = sessions.add_subparsers(dest="sessions_cmd", required=True)
    sessions_sub.add_parser("list")

    skills = sub.add_parser("skills", help="list skills")
    skills_sub = skills.add_subparsers(dest="skills_cmd", required=True)
    skills_sub.add_parser("list")

    config_cmd = sub.add_parser("config", help="show effective config")
    config_sub = config_cmd.add_subparsers(dest="config_sub", required=True)
    config_sub.add_parser("show")

    model_cmd = sub.add_parser("model", help="show model info")
    model_sub = model_cmd.add_subparsers(dest="model_sub", required=True)
    model_sub.add_parser("show")

    control = sub.add_parser("control", help="send runtime control signal")
    control.add_argument("signal", choices=["interrupt", "pause", "retry", "reverse"])

    sub.add_parser("doctor", help="environment diagnostics")
    return parser


def _build_runtime_options(args: argparse.Namespace) -> RuntimeOptions:
    workspace_dir = Path(args.workspace).expanduser().resolve()
    user_dir = Path(args.user_dir).expanduser().resolve()
    workspace_dir.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    return RuntimeOptions(
        workspace_dir=workspace_dir,
        user_dir=user_dir,
        model=args.model,
        adapter=args.adapter,
        api_key=args.api_key,
        endpoint=args.endpoint,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout,
        mcp_paths=list(args.mcp_path) if args.mcp_path else None,
        system_prompt_mode=args.system_prompt_mode,
        system_prompt_text=args.system_prompt_text,
        system_prompt_file=args.system_prompt_file,
    )


def _validate_cli_args(args: argparse.Namespace, *, output: OutputFacade) -> int | None:
    """Reject unsupported or conflicting CLI flag combinations before runtime boot."""

    if getattr(args, "headless", False) and args.output != "human":
        output.display(
            "cannot combine --headless with legacy --output; headless uses a dedicated protocol stream",
            level="error",
        )
        return 2
    if getattr(args, "control_stdin", False) and not getattr(args, "headless", False):
        output.display(
            "--control-stdin requires --headless; interactive and legacy modes do not expose the host control plane",
            level="error",
        )
        return 2
    if args.system_prompt_text is not None and args.system_prompt_file is not None:
        output.display(
            "--system-prompt-text and --system-prompt-file are mutually exclusive",
            level="error",
        )
        return 2

    if getattr(args, "command", None) in {"chat", "run", "script"}:
        try:
            _ = _resolve_resume_target(
                resume=getattr(args, "resume", None),
                session_id=getattr(args, "session_id", None),
            )
        except ValueError as exc:
            output.display(str(exc), level="error")
            return 2

    return None


async def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    configure_cli_logging(resolve_cli_log_path())
    output = OutputFacade("headless" if getattr(args, "headless", False) else args.output)
    validation_error = _validate_cli_args(args, output=output)
    if validation_error is not None:
        return validation_error
    try:
        options = _build_runtime_options(args)
    except OSError as exc:
        output.display(f"invalid runtime path: {exc}", level="error")
        return 2
    runtime = None
    exit_code = 0
    try:
        command = args.command
        try:
            provider, config = load_effective_config(options)
        except (OSError, ValueError) as exc:
            output.display(f"invalid config: {exc}", level="error")
            return 2
        _ = provider
        configure_cli_logging(resolve_cli_log_path(config))
        session_store = ClientSessionStore(config.workspace_dir)

        if not output.is_headless:
            output.header("DARE CLIENT CLI")
            output.info(f"workspace={config.workspace_dir}")
            output.info(f"adapter={config.llm.adapter or 'openai'}")
            output.info(f"model={config.llm.model}")

        if command == "doctor":
            model_probe_error: str | None = None
            try:
                model_manager = DefaultModelAdapterManager(config=config)
                _ = model_manager.load_model_adapter(config=config)
            except Exception as exc:  # noqa: BLE001
                model_probe_error = str(exc)
            payload = build_doctor_report(
                config=config,
                model_probe_error=model_probe_error,
            )
            output.emit_data(_serialize(payload))
            return 0 if payload.get("ok") else 3

        if command == "sessions":
            if args.sessions_cmd != "list":
                output.display(f"unknown sessions command: {args.sessions_cmd}", level="error")
                return 2
            output.emit_data(_serialize(_list_session_payload(session_store=session_store)))
            return 0

        # --full-auto: inject AutoUserInputHandler so ask_user never blocks.
        full_auto = getattr(args, "full_auto", False)
        if full_auto:
            from dataclasses import replace as _replace

            from dare_framework.tool._internal.tools.ask_user import AutoUserInputHandler

            options = _replace(options, user_input_handler=AutoUserInputHandler())
            output.info("full-auto mode: ask_user will auto-respond without human input")

        try:
            runtime = await bootstrap_runtime(options)
        except Exception as exc:  # noqa: BLE001
            output.display(f"runtime bootstrap failed: {exc}", level="error")
            return 1
        action_client = TransportActionClient(runtime.client_channel, timeout_seconds=args.timeout)
        resume_target = _resolve_resume_target(
            resume=getattr(args, "resume", None),
            session_id=getattr(args, "session_id", None),
        )

        if command == "chat":
            lines = None
            if args.script:
                lines = _load_script_lines_with_handling(Path(args.script), output=output)
                if lines is None:
                    return 2
            try:
                state, resume_metadata = _build_session_state(
                    mode=args.mode,
                    resume=resume_target,
                    runtime=runtime,
                    session_store=session_store,
                )
            except (SessionStoreError, RuntimeError) as exc:
                output.display(f"resume failed: {exc}", level="error")
                return 2
            return await _run_chat(
                runtime=runtime,
                action_client=action_client,
                output=output,
                mode=args.mode,
                script_lines=lines,
                approval_timeout_seconds=None,
                control_stdin=False,
                initial_state=state,
                session_store=session_store,
                resume_metadata=resume_metadata,
            )

        if command == "run":
            try:
                state, resume_metadata = _build_session_state(
                    mode=args.mode,
                    resume=resume_target,
                    runtime=runtime,
                    session_store=session_store,
                )
            except (SessionStoreError, RuntimeError) as exc:
                output.display(f"resume failed: {exc}", level="error")
                return 2
            if output.is_headless:
                output.set_protocol_context(session_id=state.conversation_id, run_id=state.conversation_id)
                payload = {
                    "mode": state.mode.value,
                    "entrypoint": "run",
                    "task": args.task,
                    "workspace": config.workspace_dir,
                    "adapter": config.llm.adapter or "openai",
                    "model": config.llm.model,
                }
                if resume_metadata is not None:
                    payload["resumed"] = True
                    payload["resume_requested"] = resume_metadata.requested
                    payload["restored_messages"] = resume_metadata.restored_messages
                output.emit_event("session.started", payload)
            if state.mode == ExecutionMode.PLAN:
                try:
                    plan = await preview_plan(
                        task_text=args.task,
                        model=runtime.model,
                        workspace_dir=runtime.config.workspace_dir,
                        user_dir=runtime.config.user_dir,
                    )
                except Exception as exc:  # noqa: BLE001
                    output.display(f"plan preview failed: {exc}", level="error")
                    return 1
                output.show_plan(plan)
                if not args.approve:
                    output.display("plan only (pass --approve to execute)")
                    return 0
            auto_tools: set[str] = set()
            if args.auto_approve:
                auto_tools.update(DEFAULT_AUTO_APPROVE_TOOLS)
            if args.auto_approve_tool:
                auto_tools.update(
                    tool.strip()
                    for tool in args.auto_approve_tool
                    if isinstance(tool, str) and tool.strip()
                )
            if full_auto:
                output.info("full-auto mode: all tool approvals will be auto-granted")
            elif auto_tools:
                output.info(f"run auto-approve enabled for tools={','.join(sorted(auto_tools))}")
            approval_watch = _ApprovalWatchState()
            approval_policy = _RunApprovalPolicy(
                action_client=action_client,
                output=output,
                watch=approval_watch,
                auto_approve_tools=auto_tools,
                auto_approve_all=full_auto,
            )

            async def _handle_run_approval_pending(
                request: dict[str, Any],
                tool_name: str,
                capability_id: str,
            ) -> None:
                request_id = str(request.get("request_id", "?")).strip() or "?"
                state.mark_runtime_approval_pending(request_id)
                await approval_policy.on_pending(request_id, tool_name, capability_id)

            def _handle_run_approval_resolved(request_id: str) -> None:
                state.mark_runtime_approval_resolved(request_id)
                approval_watch.mark_resolved(request_id)

            pump = EventPump(
                client_channel=runtime.client_channel,
                on_event=lambda payload: _on_transport_event(
                    payload,
                    output=output,
                    on_approval_pending=_handle_run_approval_pending,
                    on_approval_resolved=_handle_run_approval_resolved,
                ),
            )
            pump.start()
            control_task: asyncio.Task[None] | None = None
            if args.control_stdin:
                control_task = asyncio.create_task(
                    _run_control_stdin_loop(
                        state=state,
                        runtime=runtime,
                        action_client=action_client,
                        session_store=session_store,
                        output=output,
                    )
                )
            state.status = SessionStatus.RUNNING
            state.active_execution_description = args.task
            try:
                success = await _execute_task_with_approval_timeout(
                    runtime=runtime,
                    output=output,
                    state=state,
                    task_text=args.task,
                    approval_watch=approval_watch,
                    approval_timeout_seconds=args.approval_timeout_seconds,
                )
            finally:
                state.active_execution_description = None
                if control_task is not None:
                    control_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await control_task
                await pump.stop()
            try:
                _persist_session_snapshot(runtime=runtime, state=state, session_store=session_store)
            except (OSError, SessionStoreError, RuntimeError) as exc:
                output.display(f"failed to persist session snapshot: {exc}", level="error")
                return 1
            return 0 if success else 1

        if command == "script":
            lines = _load_script_lines_with_handling(Path(args.file), output=output)
            if lines is None:
                return 2
            script_approval_timeout_seconds = args.approval_timeout_seconds
            if script_approval_timeout_seconds is None and output.is_headless:
                script_approval_timeout_seconds = 120.0
            try:
                state, resume_metadata = _build_session_state(
                    mode=args.mode,
                    resume=resume_target,
                    runtime=runtime,
                    session_store=session_store,
                )
            except (SessionStoreError, RuntimeError) as exc:
                output.display(f"resume failed: {exc}", level="error")
                return 2
            return await _run_chat(
                runtime=runtime,
                action_client=action_client,
                output=output,
                mode=args.mode,
                script_lines=lines,
                approval_timeout_seconds=script_approval_timeout_seconds,
                control_stdin=args.control_stdin,
                initial_state=state,
                session_store=session_store,
                resume_metadata=resume_metadata,
            )

        if command == "approvals":
            tokens = [args.approvals_cmd]
            if args.approvals_cmd == "poll":
                if args.timeout_ms is not None:
                    tokens.append(f"timeout_ms={args.timeout_ms}")
                if args.timeout_seconds is not None:
                    tokens.append(f"timeout_seconds={args.timeout_seconds}")
            elif args.approvals_cmd in {"grant", "deny"}:
                tokens.append(args.request_id)
                tokens.append(f"scope={args.scope}")
                tokens.append(f"matcher={args.matcher}")
                if args.matcher_value:
                    tokens.append(f"matcher_value={args.matcher_value}")
                if args.session_id:
                    tokens.append(f"session_id={args.session_id}")
            elif args.approvals_cmd == "revoke":
                tokens.append(args.rule_id)
            payload = await handle_approvals_tokens(tokens, action_client=action_client)
            output.emit_data(_serialize(payload))
            return 0

        if command == "mcp":
            tokens = [args.mcp_cmd]
            if args.mcp_cmd == "inspect" and args.tool_name:
                tokens.append(args.tool_name)
            if args.mcp_cmd == "reload":
                tokens.extend(args.paths)
            try:
                payload = await handle_mcp_tokens(tokens, runtime=runtime)
            except Exception as exc:  # noqa: BLE001
                output.display(str(exc), level="error")
                output.display("/mcp list|inspect [tool_name]|reload [paths...]|unload")
                return 1
            if "tools" in payload:
                output.display(format_mcp_inspection(payload["tools"]))
            else:
                output.emit_data(_serialize(payload))
            return 0

        if command == "tools":
            payload = await list_tools(action_client=action_client)
            output.emit_data(_serialize(payload))
            return 0

        if command == "skills":
            payload = await list_skills(action_client=action_client)
            output.emit_data(_serialize(payload))
            return 0

        if command == "config":
            payload = await show_config(action_client=action_client)
            output.emit_data(_serialize(payload))
            return 0

        if command == "model":
            payload = await show_model(action_client=action_client)
            output.emit_data(_serialize(payload))
            return 0

        if command == "control":
            payload = await send_control(args.signal, action_client=action_client)
            output.emit_data(_serialize(payload))
            return 0

        output.display(f"unknown command: {command}", level="error")
        exit_code = 2
    except ActionClientError as exc:
        output.display(str(exc), level="error")
        exit_code = 1
    except KeyboardInterrupt:
        output.display("interrupted", level="warn")
        exit_code = 130
    finally:
        if runtime is not None:
            close = getattr(runtime, "close", None)
            if callable(close):
                result = close()
                if hasattr(result, "__await__"):
                    await result
    return exit_code


def sync_main(argv: list[str] | None = None) -> int:
    """Synchronous wrapper used by console script entrypoints."""
    return asyncio.run(main(argv))


def cli() -> None:
    """Console script entrypoint for ``dare``."""
    raise SystemExit(sync_main())
