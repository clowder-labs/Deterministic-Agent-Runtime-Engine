"""Unified external CLI for DARE framework."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

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
from client.render.human import HumanRenderer
from client.render.json import JsonRenderer
from client.runtime.action_client import ActionClientError, TransportActionClient
from client.runtime.bootstrap import RuntimeOptions, bootstrap_runtime, load_effective_config
from client.runtime.event_stream import EventPump
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

    @property
    def mode(self) -> str:
        return self._mode

    def header(self, title: str) -> None:
        if self._human is not None:
            self._human.header(title)
            return
        self._json.emit({"type": "event", "event": "header", "data": {"title": title}})

    def info(self, text: str) -> None:
        if self._human is not None:
            self._human.info(text)
            return
        self._json.emit({"type": "log", "level": "info", "message": text})

    def warn(self, text: str) -> None:
        if self._human is not None:
            self._human.warn(text)
            return
        self._json.emit({"type": "log", "level": "warn", "message": text})

    def ok(self, text: str) -> None:
        if self._human is not None:
            self._human.ok(text)
            return
        self._json.emit({"type": "log", "level": "ok", "message": text})

    def error(self, text: str) -> None:
        if self._human is not None:
            self._human.error(text)
            return
        self._json.emit({"type": "log", "level": "error", "message": text})

    def show_mode(self, mode: ExecutionMode) -> None:
        if self._human is not None:
            self._human.show_mode(mode)
            return
        self._json.emit({"type": "event", "event": "mode", "data": {"mode": mode.value}})

    def show_plan(self, plan: Any) -> None:
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
        self._json.emit({"type": "event", "event": "plan_preview", "data": payload})

    def emit_data(self, payload: Any) -> None:
        if self._human is not None:
            print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
            return
        self._json.emit({"type": "result", "data": payload})

    def emit_event(self, event: str, payload: Any) -> None:
        if self._human is not None:
            print(json.dumps({"event": event, "payload": payload}, ensure_ascii=False), flush=True)
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
        output.error(f"failed to load script file: {exc}")
        return None


def _is_execution_running(state: CLISessionState) -> bool:
    task = state.active_execution_task
    return task is not None and not task.done()


async def _execute_task_and_report(
    *,
    runtime: Any,
    output: OutputFacade,
    state: CLISessionState,
    task_text: str,
) -> bool:
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
        output.warn("execution cancelled")
        return False
    except Exception as exc:  # noqa: BLE001
        state.last_execution_success = False
        state.execution_failures += 1
        output.error(f"execution error: {exc}")
        return False

    if result.success:
        state.last_execution_success = True
        output.ok("task completed")
        text = format_run_output(result.output)
        if text:
            output.info(text)
        return True

    state.last_execution_success = False
    state.execution_failures += 1
    output.error("task failed")
    if result.errors:
        output.error(f"errors: {result.errors}")
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
        output.warn("execution cancelled")
    except Exception as exc:  # noqa: BLE001
        output.error(f"execution failed: {exc}")
    finally:
        state.active_execution_task = None
        state.active_execution_description = None
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


def _normalize_mode(value: str) -> ExecutionMode:
    return ExecutionMode.PLAN if value == "plan" else ExecutionMode.EXECUTE


@dataclasses.dataclass
class _ApprovalWatchState:
    """Track the currently pending approval request for timeout enforcement."""

    request_id: str | None = None
    pending_since_monotonic: float | None = None

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
        "write_file",
    }
)


@dataclasses.dataclass
class _RunApprovalPolicy:
    """Auto-approval policy used by `run` mode transport event handling."""

    action_client: TransportActionClient
    output: OutputFacade
    watch: _ApprovalWatchState
    auto_approve_tools: set[str]
    seen_disallowed: set[str] = dataclasses.field(default_factory=set)
    attempted: set[str] = dataclasses.field(default_factory=set)

    async def on_pending(self, request_id: str, tool_name: str, capability_id: str) -> None:
        normalized_request = request_id.strip() if request_id.strip() else "?"
        normalized_tool = tool_name.strip() if tool_name.strip() else "?"
        self.watch.mark_pending(normalized_request)
        if not self.auto_approve_tools:
            return

        if normalized_tool not in self.auto_approve_tools:
            if normalized_request in self.seen_disallowed:
                return
            self.seen_disallowed.add(normalized_request)
            self.output.warn(
                "auto-approve skipped: "
                f"request_id={normalized_request}, tool={normalized_tool}, capability={capability_id}"
            )
            self.output.warn(
                "rerun with `--auto-approve-tool "
                f"{normalized_tool}` to allow this tool in run mode"
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
            self.output.error(
                f"auto-approve failed for request_id={normalized_request}: {exc}"
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
                    output.error(
                        "approval wait timed out "
                        f"(request_id={request_id}, timeout={approval_timeout_seconds:.1f}s)"
                    )
                    output.error(
                        "rerun with `--auto-approve-tool <tool_name>` "
                        "or use `chat` mode to approve manually"
                    )
                    task.cancel()
                    break
            await asyncio.sleep(0.1)

        try:
            return await task
        except asyncio.CancelledError:
            return False
    finally:
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
) -> bool:
    if command.type == CommandType.QUIT:
        if _is_execution_running(state):
            output.warn("cancelling running execution")
            assert state.active_execution_task is not None
            state.active_execution_task.cancel()
            await _finalize_background_task_if_done(state, output=output)
        output.info("bye")
        return True

    if command.type == CommandType.HELP:
        output.info(
            "/mode [plan|execute], /approve, /reject, /status, "
            "/approvals [...], /mcp [...], /tools list, /skills list, "
            "/config show, /model show, /interrupt, /quit"
        )
        return False

    if command.type == CommandType.STATUS:
        running = _is_execution_running(state)
        output.info(f"status={state.status.value}, mode={state.mode.value}, running={running}")
        if running and state.active_execution_description:
            output.info(f"active_task={state.active_execution_description}")
        return False

    if command.type == CommandType.MODE:
        if not command.args:
            output.warn("/mode requires plan or execute")
            return False
        mode = command.args[0].strip().lower()
        if mode not in {"plan", "execute"}:
            output.warn(f"unknown mode: {mode}")
            return False
        state.mode = _normalize_mode(mode)
        output.show_mode(state.mode)
        return False

    if command.type == CommandType.APPROVE:
        if state.pending_task_description is None:
            output.warn("no pending plan")
            return False
        task_text = state.pending_task_description
        if background_execute and _is_execution_running(state):
            output.warn("another execution is running")
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
        await _execute_task_and_report(
            runtime=runtime,
            output=output,
            state=state,
            task_text=task_text,
        )
        state.status = SessionStatus.IDLE
        return False

    if command.type == CommandType.REJECT:
        state.clear_pending()
        if not _is_execution_running(state):
            state.status = SessionStatus.IDLE
        output.info("plan rejected")
        return False

    if command.type == CommandType.APPROVALS:
        try:
            payload = await handle_approvals_tokens(command.args, action_client=action_client)
        except Exception as exc:  # noqa: BLE001
            output.error(str(exc))
            for line in approvals_usage_lines():
                output.info(line)
            return False
        output.emit_data(_serialize(payload))
        return False

    if command.type == CommandType.MCP:
        try:
            payload = await handle_mcp_tokens(command.args, runtime=runtime)
        except Exception as exc:  # noqa: BLE001
            output.error(str(exc))
            output.info("/mcp list|inspect [tool_name]|reload [paths...]|unload")
            return False
        if "tools" in payload:
            output.info(format_mcp_inspection(payload["tools"]))
        else:
            output.emit_data(_serialize(payload))
        return False

    if command.type == CommandType.TOOLS:
        payload = await list_tools(action_client=action_client)
        output.emit_data(_serialize(payload))
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
                )
            except ActionClientError as exc:
                # Command failures must affect scripted exit status.
                state.last_execution_success = False
                state.execution_failures += 1
                output.error(str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                # Keep command exceptions visible while preserving deterministic script rc.
                state.last_execution_success = False
                state.execution_failures += 1
                output.error(f"command failed: {exc}")
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
                output.error(f"plan preview failed: {exc}")
                continue
            state.status = SessionStatus.AWAITING_APPROVAL
            output.show_plan(state.pending_plan)
            output.info("type /approve to execute or /reject to cancel")
            continue

        if background_execute:
            if _is_execution_running(state):
                output.warn("another execution is running")
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
        await _execute_task_and_report(
            runtime=runtime,
            output=output,
            state=state,
            task_text=task_text,
        )
        state.status = SessionStatus.IDLE

    await _finalize_background_task_if_done(state, output=output)
    return quit_requested


def _on_transport_event(
    payload: dict[str, Any],
    *,
    output: OutputFacade,
    on_approval_pending: Callable[[str, str, str], Awaitable[None] | None] | None = None,
    on_approval_resolved: Callable[[str], Awaitable[None] | None] | None = None,
) -> Awaitable[None] | None:
    return _on_transport_event_async(
        payload,
        output=output,
        on_approval_pending=on_approval_pending,
        on_approval_resolved=on_approval_resolved,
    )


async def _on_transport_event_async(
    payload: dict[str, Any],
    *,
    output: OutputFacade,
    on_approval_pending: Callable[[str, str, str], Awaitable[None] | None] | None = None,
    on_approval_resolved: Callable[[str], Awaitable[None] | None] | None = None,
) -> None:
    payload_type = payload.get("type")
    if payload_type == "approval_pending":
        resp = payload.get("resp", {})
        request = resp.get("request", {}) if isinstance(resp, dict) else {}
        request_id = str(request.get("request_id", "?"))
        capability_id = str(resp.get("capability_id", "?")) if isinstance(resp, dict) else "?"
        tool_name = str(resp.get("tool_name", "?")) if isinstance(resp, dict) else "?"
        if on_approval_pending is not None:
            maybe_awaitable = on_approval_pending(request_id, tool_name, capability_id)
            if maybe_awaitable is not None:
                await maybe_awaitable
        output.warn(f"approval pending: request_id={request_id}, capability={capability_id}")
        return
    if payload_type == "approval_resolved":
        resp = payload.get("resp", {})
        request_id = str(resp.get("request_id", "?")) if isinstance(resp, dict) else "?"
        decision = resp.get("decision", "?") if isinstance(resp, dict) else "?"
        if on_approval_resolved is not None:
            maybe_awaitable = on_approval_resolved(request_id)
            if maybe_awaitable is not None:
                await maybe_awaitable
        output.info(f"approval resolved: request_id={request_id}, decision={decision}")
        return
    if payload_type == "hook":
        output.info(f"hook event: {payload.get('event')}")
        return
    # Keep unknown payloads observable in json mode while avoiding noisy human logs.
    if output.mode == "json":
        output.emit_event("transport", _serialize(payload))


async def _run_chat(
    *,
    runtime: Any,
    action_client: TransportActionClient,
    output: OutputFacade,
    mode: str,
    script_lines: list[str] | None,
) -> int:
    state = CLISessionState(mode=_normalize_mode(mode))
    output.show_mode(state.mode)
    pump = EventPump(
        client_channel=runtime.client_channel,
        on_event=lambda payload: _on_transport_event(payload, output=output),
    )
    pump.start()
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
            )
            if _is_execution_running(state):
                output.warn("waiting for last background execution")
                await _wait_for_background_task(state, output=output)
            return 0 if state.execution_failures == 0 else 1

        output.info("type /help for commands. /quit to exit.")
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
            )
            if quit_requested:
                break
        if _is_execution_running(state):
            output.warn("waiting for running execution")
            await _wait_for_background_task(state, output=output)
        return 0
    finally:
        await pump.stop()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DARE external CLI")
    parser.add_argument("--workspace", default=str(Path.cwd()), help="workspace root path")
    parser.add_argument("--user-dir", default=str(Path.home()), help="user directory path")
    parser.add_argument("--adapter", default=None, help="llm adapter override (openai/openrouter)")
    parser.add_argument("--model", default=None, help="llm model override")
    parser.add_argument("--api-key", default=None, help="llm api key override")
    parser.add_argument("--endpoint", default=None, help="llm endpoint override")
    parser.add_argument("--max-tokens", type=int, default=None, help="max tokens override")
    parser.add_argument("--timeout", type=float, default=60.0, help="request timeout seconds")
    parser.add_argument("--mcp-path", action="append", default=None, help="extra MCP path override (repeatable)")
    parser.add_argument("--output", choices=["human", "json"], default="human")

    sub = parser.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="interactive chat mode")
    chat.add_argument("--mode", choices=["plan", "execute"], default="execute")
    chat.add_argument("--script", default=None, help="optional script file")

    run = sub.add_parser("run", help="run one task and exit")
    run.add_argument("--task", required=True)
    run.add_argument("--mode", choices=["plan", "execute"], default="execute")
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

    script = sub.add_parser("script", help="run script and exit")
    script.add_argument("--file", required=True)
    script.add_argument("--mode", choices=["plan", "execute"], default="execute")

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
    )


async def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    output = OutputFacade(args.output)
    try:
        options = _build_runtime_options(args)
    except OSError as exc:
        output.error(f"invalid runtime path: {exc}")
        return 2
    runtime = None
    exit_code = 0
    try:
        command = args.command
        try:
            provider, config = load_effective_config(options)
        except (OSError, ValueError) as exc:
            output.error(f"invalid config: {exc}")
            return 2
        _ = provider

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

        try:
            runtime = await bootstrap_runtime(options)
        except Exception as exc:  # noqa: BLE001
            output.error(f"runtime bootstrap failed: {exc}")
            return 1
        action_client = TransportActionClient(runtime.client_channel, timeout_seconds=args.timeout)

        if command == "chat":
            lines = None
            if args.script:
                lines = _load_script_lines_with_handling(Path(args.script), output=output)
                if lines is None:
                    return 2
            return await _run_chat(
                runtime=runtime,
                action_client=action_client,
                output=output,
                mode=args.mode,
                script_lines=lines,
            )

        if command == "run":
            state = CLISessionState(mode=_normalize_mode(args.mode))
            if state.mode == ExecutionMode.PLAN:
                try:
                    plan = await preview_plan(
                        task_text=args.task,
                        model=runtime.model,
                        workspace_dir=runtime.config.workspace_dir,
                        user_dir=runtime.config.user_dir,
                    )
                except Exception as exc:  # noqa: BLE001
                    output.error(f"plan preview failed: {exc}")
                    return 1
                output.show_plan(plan)
                if not args.approve:
                    output.info("plan only (pass --approve to execute)")
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
            if auto_tools:
                output.info(f"run auto-approve enabled for tools={','.join(sorted(auto_tools))}")
            approval_watch = _ApprovalWatchState()
            approval_policy = _RunApprovalPolicy(
                action_client=action_client,
                output=output,
                watch=approval_watch,
                auto_approve_tools=auto_tools,
            )
            pump = EventPump(
                client_channel=runtime.client_channel,
                on_event=lambda payload: _on_transport_event(
                    payload,
                    output=output,
                    on_approval_pending=approval_policy.on_pending,
                    on_approval_resolved=approval_watch.mark_resolved,
                ),
            )
            pump.start()
            state.status = SessionStatus.RUNNING
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
                await pump.stop()
            return 0 if success else 1

        if command == "script":
            lines = _load_script_lines_with_handling(Path(args.file), output=output)
            if lines is None:
                return 2
            return await _run_chat(
                runtime=runtime,
                action_client=action_client,
                output=output,
                mode=args.mode,
                script_lines=lines,
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
                output.error(str(exc))
                output.info("/mcp list|inspect [tool_name]|reload [paths...]|unload")
                return 1
            if "tools" in payload:
                output.info(format_mcp_inspection(payload["tools"]))
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

        output.error(f"unknown command: {command}")
        exit_code = 2
    except ActionClientError as exc:
        output.error(str(exc))
        exit_code = 1
    except KeyboardInterrupt:
        output.warn("interrupted")
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
