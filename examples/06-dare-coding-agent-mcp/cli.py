"""Interactive CLI for the DARE coding agent example with MCP support.

This example is based on 04-dare-coding-agent and adds:
- config-based MCP loading (.dare/config.json -> mcp_paths)
- runtime MCP commands (/mcp list|reload|unload)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import DareAgentBuilder
from dare_framework.config import Config, FileConfigProvider
from dare_framework.context import Context, Message
from dare_framework.event.kernel import IEventLog
from dare_framework.event.types import Event, RuntimeSnapshot
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.plan import DefaultPlanner, DefaultRemediator, Task
from dare_framework.tool._internal.tools import ReadFileTool, RunCommandTool, SearchCodeTool, WriteFileTool
from dare_framework.transport import AgentChannel, DirectClientChannel, EnvelopeKind, TransportEnvelope, new_envelope_id
from dare_framework.transport.interaction.resource_action import ResourceAction

from validators.file_validator import FileExistsValidator


class CommandType(Enum):
    QUIT = "quit"
    MODE = "mode"
    APPROVE = "approve"
    REJECT = "reject"
    STATUS = "status"
    APPROVALS = "approvals"
    MCP = "mcp"
    HELP = "help"


class ExecutionMode(Enum):
    PLAN = "plan"
    EXECUTE = "execute"


class SessionStatus(Enum):
    IDLE = "idle"
    AWAITING_APPROVAL = "awaiting"
    RUNNING = "running"
    COMPLETED = "completed"


@dataclass
class Command:
    type: CommandType
    args: list[str]
    raw_input: str


@dataclass
class CLISessionState:
    mode: ExecutionMode = ExecutionMode.EXECUTE
    status: SessionStatus = SessionStatus.IDLE
    pending_plan: Any | None = None
    pending_task_description: str | None = None
    active_execution_task: asyncio.Task[Any] | None = None
    active_execution_description: str | None = None

    def reset_task(self) -> None:
        self.pending_plan = None
        self.pending_task_description = None


@dataclass
class MCPRuntimeState:
    config_provider: FileConfigProvider
    config: Config
    config_base_dir: Path


def _normalize_mcp_paths(paths: list[str], base_dir: Path) -> list[str]:
    normalized: list[str] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            # Keep config authoring friendly (relative paths) while runtime uses absolute paths.
            path = (base_dir / path).resolve()
        normalized.append(str(path))
    return normalized


def _resolve_config_paths(config: Config, base_dir: Path) -> Config:
    if not config.mcp_paths:
        return config
    normalized_paths = _normalize_mcp_paths(list(config.mcp_paths), base_dir)
    if normalized_paths == list(config.mcp_paths):
        return config
    return replace(config, mcp_paths=normalized_paths)


def parse_command(user_input: str) -> Command | tuple[None, str]:
    stripped = user_input.strip()

    if not stripped.startswith("/"):
        return (None, stripped)

    parts = stripped[1:].split(maxsplit=1)
    cmd_name = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []

    command_map = {
        "quit": CommandType.QUIT,
        "exit": CommandType.QUIT,
        "q": CommandType.QUIT,
        "mode": CommandType.MODE,
        "approve": CommandType.APPROVE,
        "reject": CommandType.REJECT,
        "status": CommandType.STATUS,
        "approvals": CommandType.APPROVALS,
        "mcp": CommandType.MCP,
        "help": CommandType.HELP,
    }

    if cmd_name not in command_map:
        return (None, stripped)

    return Command(type=command_map[cmd_name], args=args, raw_input=user_input)


def load_script_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


class CLIDisplay:
    def __init__(self, *, width: int = 72) -> None:
        self._width = width

    def header(self, title: str) -> None:
        rule = "=" * self._width
        print(f"\n{rule}\n{title}\n{rule}\n", flush=True)

    def info(self, text: str) -> None:
        print(f"[INFO] {text}", flush=True)

    def warn(self, text: str) -> None:
        print(f"[WARN] {text}", flush=True)

    def ok(self, text: str) -> None:
        print(f"[OK] {text}", flush=True)

    def error(self, text: str) -> None:
        print(f"[ERR] {text}", flush=True)

    def show_mode(self, mode: ExecutionMode) -> None:
        self.info(f"mode={mode.value}")

    def show_tool_lists(self, agent: Any) -> None:
        """Print MCP tool list and local tool list."""
        try:
            list_tool_defs = getattr(agent, "list_tool_defs", None)
            if callable(list_tool_defs):
                tools = list_tool_defs()
            else:
                gateway = getattr(getattr(agent, "context", None), "_tool_gateway", None)
                if gateway is None:
                    self.info("tools: (none)")
                    return
                tools = gateway.list_tools()
        except Exception:
            self.info("tools: (unable to list)")
            return

        def _tool_name(tool: Any) -> str:
            if isinstance(tool, dict):
                metadata = tool.get("metadata")
                if isinstance(metadata, dict) and isinstance(metadata.get("display_name"), str):
                    return metadata["display_name"]
                function = tool.get("function")
                if isinstance(function, dict) and isinstance(function.get("name"), str):
                    return function["name"]
                return str(tool.get("capability_id", tool))
            return getattr(tool, "name", str(tool))

        mcp_tools = [item for item in tools if ":" in _tool_name(item)]
        local_tools = [item for item in tools if ":" not in _tool_name(item)]
        names = lambda items: [_tool_name(item) for item in items]
        self.info(f"MCP tools ({len(mcp_tools)}): {names(mcp_tools) if mcp_tools else []}")
        self.info(f"Local tools ({len(local_tools)}): {names(local_tools) if local_tools else []}")

    def show_plan(self, plan: Any) -> None:
        self.header("PLAN PREVIEW")
        print(f"Goal: {plan.plan_description}\n", flush=True)
        if not plan.steps:
            print("(no steps)", flush=True)
            return
        for index, step in enumerate(plan.steps, 1):
            print(f"{index}. {step.description or step.capability_id}", flush=True)
            print(f"   evidence: {step.capability_id}", flush=True)
            if step.params:
                print(f"   params: {step.params}", flush=True)
        print(flush=True)

    def show_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if event_type == "plan.validated":
            self.ok("plan validated")
            return
        if event_type == "plan.invalid":
            self.error(f"plan invalid: {payload.get('errors')}")
            return
        if event_type == "model.response":
            iteration = payload.get("iteration")
            has_tools = payload.get("has_tool_calls")
            self.info(f"model response (iter={iteration}, tool_calls={has_tools})")
            return
        if event_type == "tool.invoke":
            name = payload.get("capability_id") or payload.get("tool") or "?"
            attempt = payload.get("attempt")
            self.info(f"tool invoke: {name} (attempt {attempt})")
            return
        if event_type == "tool.result":
            name = payload.get("capability_id") or payload.get("tool") or "?"
            success = payload.get("success", True)
            if success:
                self.ok(f"tool result: {name}")
            else:
                self.warn(f"tool result failed: {name}")
            return
        if event_type == "tool.error":
            name = payload.get("capability_id") or payload.get("tool") or "?"
            err = payload.get("error")
            self.error(f"tool error: {name} ({err})")
            return
        if event_type == "milestone.success":
            self.ok("milestone success")
            return
        if event_type == "milestone.failed":
            self.error("milestone failed")
            return


class StreamingEventLog(IEventLog):
    def __init__(self, on_event: callable) -> None:
        self._on_event = on_event
        self._events: list[Event] = []

    async def append(self, event_type: str, payload: dict[str, Any]) -> str:
        self._on_event(event_type, payload)
        event = Event(event_type=event_type, payload=payload)
        self._events.append(event)
        return event.event_id

    async def query(self, *, filter: dict[str, Any] | None = None, limit: int = 100) -> list[Event]:
        if filter is None:
            return list(self._events)[-limit:]
        return [event for event in self._events if _match_filter(event, filter)][-limit:]

    async def replay(self, *, from_event_id: str) -> RuntimeSnapshot:
        return RuntimeSnapshot(from_event_id=from_event_id, events=list(self._events))

    async def verify_chain(self) -> bool:
        return True


def _match_filter(event: Event, filter: dict[str, Any]) -> bool:
    for key, value in filter.items():
        if event.payload.get(key) != value:
            return False
    return True


async def build_agent(
    workspace: Path,
    model_name: str,
    api_key: str,
    max_tokens: int,
    timeout_seconds: float,
    display: CLIDisplay,
    config: Config,
    *,
    agent_channel: AgentChannel | None = None,
) -> Any:
    model = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
        http_client_options={"timeout": timeout_seconds},
    )
    tools = [ReadFileTool(), WriteFileTool(), SearchCodeTool(), RunCommandTool()]
    validator = FileExistsValidator(
        workspace=workspace,
        expected_files=[],
        verbose=False,
    )

    event_log = StreamingEventLog(display.show_event)

    builder = (
        DareAgentBuilder("dare-coding-agent-mcp")
        .with_model(model)
        .with_config(config)
        .add_tools(*tools)
        .with_planner(DefaultPlanner(model, verbose=False))
        .add_validators(validator)
        .with_remediator(DefaultRemediator(model, verbose=False))
        .with_event_log(event_log)
    )
    if agent_channel is not None:
        builder = builder.with_agent_channel(agent_channel)

    agent = await builder.build()
    return agent


async def preview_plan(task_text: str, model: OpenRouterModelAdapter, display: CLIDisplay) -> Any:
    ctx = Context(
        id="plan-preview",
        config=Config(workspace_dir=str(PROJECT_ROOT), user_dir=str(Path.home())),
    )
    ctx.stm_add(Message(role="user", content=task_text))
    planner = DefaultPlanner(model, verbose=False)
    plan = await planner.plan(ctx)
    display.show_plan(plan)
    return plan


def _format_result_output(output: Any) -> str | None:
    """Extract displayable text from RunResult.output."""
    if output is None:
        return None
    if isinstance(output, str):
        return output.strip() or None
    if isinstance(output, dict) and "content" in output:
        text = output["content"]
        if text is None:
            return None
        normalized = text.strip() if isinstance(text, str) else str(text).strip()
        return normalized or None
    return str(output).strip() or None


def _network_error_hint(exc: Exception) -> str | None:
    summary = f"{type(exc).__name__}: {exc}".lower()
    if "apiconnectionerror" not in summary and "connecterror" not in summary and "connection error" not in summary:
        return None

    http_proxy = os.getenv("http_proxy") or os.getenv("HTTP_PROXY")
    https_proxy = os.getenv("https_proxy") or os.getenv("HTTPS_PROXY")
    proxy = http_proxy or https_proxy
    if proxy and ("127.0.0.1" in proxy or "localhost" in proxy):
        return (
            f"detected local proxy {proxy}. if your local proxy is not running, "
            "unset HTTP(S)_PROXY or start the proxy first."
        )

    return "model network connection failed. check API key/network and proxy settings."


async def run_task(agent: Any, task_text: str, display: CLIDisplay) -> None:
    display.header("EXECUTION")
    try:
        result = await agent(Task(description=task_text))
    except Exception as exc:
        display.error(f"execution error: {exc}")
        hint = _network_error_hint(exc)
        if hint:
            display.warn(hint)
        return
    if result.success:
        display.ok("task completed")
        reply = _format_result_output(result.output)
        if reply:
            print("\n--- result ---\n", flush=True)
            print(reply, flush=True)
            print(flush=True)
    else:
        display.error("task failed")
        if result.errors:
            display.error(f"errors: {result.errors}")


async def _reload_mcp_provider(
    *,
    agent: Any,
    display: CLIDisplay,
    mcp_state: MCPRuntimeState,
    paths: list[str] | None = None,
) -> None:
    reload_mcp = getattr(agent, "reload_mcp", None)
    if not callable(reload_mcp):
        display.warn("current gateway does not support dynamic MCP registration")
        return

    latest_config = mcp_state.config_provider.reload()
    mcp_state.config = _resolve_config_paths(latest_config, mcp_state.config_base_dir)
    effective_paths = _normalize_mcp_paths(paths, mcp_state.config_base_dir) if paths else None

    try:
        await reload_mcp(config=mcp_state.config, paths=effective_paths)
    except Exception as exc:
        display.error(f"failed to reload MCP provider: {exc}")
        return

    display.ok("MCP reloaded")
    display.show_tool_lists(agent)


async def _unload_mcp_provider(
    *,
    agent: Any,
    display: CLIDisplay,
    mcp_state: MCPRuntimeState,
) -> None:
    unload_mcp = getattr(agent, "unload_mcp", None)
    if not callable(unload_mcp):
        display.warn("current gateway does not support dynamic MCP registration")
        return

    try:
        removed = await unload_mcp()
    except Exception as exc:
        display.error(f"failed to unload MCP provider: {exc}")
        return

    if removed:
        display.ok("MCP unloaded")
    else:
        display.warn("tracked MCP provider was not registered; cleared runtime state")
    display.show_tool_lists(agent)


def _inspect_mcp_tools(
    *,
    agent: Any,
    display: CLIDisplay,
    tool_name: str | None = None,
) -> None:
    inspect_mcp_tools = getattr(agent, "inspect_mcp_tools", None)
    if not callable(inspect_mcp_tools):
        display.warn("current gateway does not support dynamic MCP registration")
        return

    try:
        mcp_tool_defs = inspect_mcp_tools(tool_name=tool_name)
    except Exception as exc:
        display.error(f"failed to inspect tools: {exc}")
        return

    if not mcp_tool_defs:
        if tool_name:
            display.warn(f"no MCP tool matched: {tool_name}")
        else:
            display.warn("no MCP tools loaded")
        return

    display.header("MCP TOOL SCHEMAS")
    for tool_def in mcp_tool_defs:
        function = tool_def.get("function", {})
        name = function.get("name", "?")
        description = function.get("description", "")
        parameters = function.get("parameters", {})

        print(f"tool: {name}", flush=True)
        if description:
            print(f"description: {description}", flush=True)
        print("parameters:", flush=True)
        print(json.dumps(parameters, ensure_ascii=False, indent=2), flush=True)
        output_schema = tool_def.get("output_schema")
        if isinstance(output_schema, dict) and output_schema:
            print("output_schema:", flush=True)
            print(json.dumps(output_schema, ensure_ascii=False, indent=2), flush=True)
        print("", flush=True)


async def _handle_mcp_command(
    args: list[str],
    *,
    agent: Any,
    display: CLIDisplay,
    mcp_state: MCPRuntimeState | None,
) -> None:
    if mcp_state is None:
        display.warn("mcp runtime controls unavailable")
        return
    if not args:
        display.info("/mcp [list|inspect [tool_name]|reload|unload]")
        return

    subcommand = args[0].lower()
    if subcommand == "list":
        display.show_tool_lists(agent)
        return
    if subcommand == "inspect":
        target_tool = args[1] if len(args) > 1 else None
        _inspect_mcp_tools(agent=agent, display=display, tool_name=target_tool)
        return
    if subcommand == "reload":
        await _reload_mcp_provider(
            agent=agent,
            display=display,
            mcp_state=mcp_state,
            paths=args[1:] if len(args) > 1 else None,
        )
        return
    if subcommand == "unload":
        await _unload_mcp_provider(agent=agent, display=display, mcp_state=mcp_state)
        return

    display.warn(f"unknown mcp command: {subcommand}")
    display.info("/mcp [list|inspect [tool_name]|reload|unload]")


def _approvals_usage(display: CLIDisplay) -> None:
    display.info("/approvals list")
    display.info("/approvals poll [timeout_ms=30000] [session_id=...]")
    display.info("/approvals grant <request_id> [scope=workspace] [matcher=exact_params] [matcher_value=...]")
    display.info("/approvals deny <request_id> [scope=once] [matcher=exact_params] [matcher_value=...]")
    display.info("/approvals revoke <rule_id>")


async def _invoke_approval_action(
    approval_client: DirectClientChannel,
    action: ResourceAction,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = dict(params or {})
    request = TransportEnvelope(
        id=new_envelope_id(),
        kind=EnvelopeKind.ACTION,
        payload=action.value,
        meta=meta,
    )
    response = await approval_client.ask(
        request,
        timeout=_approval_action_timeout_seconds(action, meta),
    )
    payload = response.payload
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected action response payload: {payload!r}")

    event_type = response.event_type
    if not isinstance(event_type, str) or not event_type:
        raise RuntimeError("invalid action response: missing event_type")
    if event_type == "error":
        raise RuntimeError(str(payload.get("reason") or payload.get("error") or "action failed"))

    resp = payload.get("resp")
    if not isinstance(resp, dict):
        raise RuntimeError(f"unexpected action response shape: {payload!r}")

    result = resp.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"unexpected action result shape: {payload!r}")
    return result


def _approval_action_timeout_seconds(action: ResourceAction, params: dict[str, Any]) -> float:
    default_timeout = 30.0
    if action != ResourceAction.APPROVALS_POLL:
        return default_timeout

    poll_timeout_seconds = _parse_poll_timeout_seconds(params)
    if poll_timeout_seconds is None:
        return default_timeout
    # Leave a small transport cushion so ask() does not time out first.
    return max(default_timeout, poll_timeout_seconds + 5.0)


def _parse_poll_timeout_seconds(params: dict[str, Any]) -> float | None:
    raw_seconds = params.get("timeout_seconds")
    raw_millis = params.get("timeout_ms")
    if raw_seconds is not None:
        seconds = float(raw_seconds)
        if seconds < 0:
            raise ValueError("timeout_seconds must be >= 0")
        return seconds
    if raw_millis is not None:
        millis = float(raw_millis)
        if millis < 0:
            raise ValueError("timeout_ms must be >= 0")
        return millis / 1000.0
    return None


def _parse_key_value_args(tokens: list[str]) -> tuple[list[str], dict[str, str]]:
    positional: list[str] = []
    options: dict[str, str] = {}
    for token in tokens:
        if "=" in token:
            key, value = token.split("=", 1)
            normalized = key.strip()
            if normalized:
                options[normalized] = value.strip()
            continue
        positional.append(token)
    return positional, options


def _build_approval_action_params(
    *,
    request_id: str,
    trailing_args: list[str],
) -> dict[str, Any]:
    _positional, options = _parse_key_value_args(trailing_args)
    params: dict[str, Any] = {"request_id": request_id}
    for key in ("scope", "matcher", "matcher_value"):
        if key in options and options[key]:
            params[key] = options[key]
    return params


def _build_approval_poll_params(trailing_args: list[str]) -> dict[str, Any]:
    _positional, options = _parse_key_value_args(trailing_args)
    params: dict[str, Any] = {}
    for key in ("timeout_ms", "timeout_seconds", "session_id"):
        if key in options and options[key]:
            params[key] = options[key]
    return params


async def _handle_approvals_command(
    args: list[str],
    *,
    approval_client: DirectClientChannel | None,
    display: CLIDisplay,
) -> None:
    if approval_client is None:
        display.warn("approval transport unavailable")
        return
    if not args:
        _approvals_usage(display)
        return

    subcommand = args[0].lower()
    try:
        if subcommand == "list":
            result = await _invoke_approval_action(approval_client, ResourceAction.APPROVALS_LIST)
            pending = result.get("pending", [])
            rules = result.get("rules", [])
            display.info(f"pending={len(pending)} rules={len(rules)}")
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            return

        if subcommand == "poll":
            params = _build_approval_poll_params(args[1:])
            result = await _invoke_approval_action(
                approval_client,
                ResourceAction.APPROVALS_POLL,
                params=params,
            )
            request = result.get("request")
            if isinstance(request, dict):
                display.info(f"pending request: {request.get('request_id', '?')}")
            else:
                display.info("no pending approval request")
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            return

        if subcommand in {"grant", "deny"}:
            if len(args) < 2:
                display.warn(f"/approvals {subcommand} requires request_id")
                _approvals_usage(display)
                return
            request_id = args[1]
            action = (
                ResourceAction.APPROVALS_GRANT
                if subcommand == "grant"
                else ResourceAction.APPROVALS_DENY
            )
            params = _build_approval_action_params(request_id=request_id, trailing_args=args[2:])
            result = await _invoke_approval_action(approval_client, action, params=params)
            display.ok(f"{subcommand} applied: {request_id}")
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            return

        if subcommand == "revoke":
            if len(args) < 2:
                display.warn("/approvals revoke requires rule_id")
                _approvals_usage(display)
                return
            rule_id = args[1]
            result = await _invoke_approval_action(
                approval_client,
                ResourceAction.APPROVALS_REVOKE,
                params={"rule_id": rule_id},
            )
            if result.get("removed"):
                display.ok(f"revoked rule: {rule_id}")
            else:
                display.warn(f"rule not found: {rule_id}")
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            return
    except Exception as exc:  # noqa: BLE001
        display.error(f"approvals command failed: {exc}")
        return

    display.warn(f"unknown approvals command: {subcommand}")
    _approvals_usage(display)


def _is_execution_running(state: CLISessionState) -> bool:
    task = state.active_execution_task
    return task is not None and not task.done()


async def _finalize_background_execution_if_done(state: CLISessionState, display: CLIDisplay) -> None:
    task = state.active_execution_task
    if task is None or not task.done():
        return

    try:
        await task
    except asyncio.CancelledError:
        display.warn("execution cancelled")
    except Exception as exc:  # noqa: BLE001
        display.error(f"execution failed: {exc}")
    finally:
        state.active_execution_task = None
        state.active_execution_description = None
        if state.status == SessionStatus.RUNNING:
            state.status = SessionStatus.IDLE


def _clear_pending_plan(state: CLISessionState) -> None:
    state.pending_plan = None
    state.pending_task_description = None


async def _start_background_execution(
    *,
    state: CLISessionState,
    agent: Any,
    task_text: str,
    display: CLIDisplay,
) -> None:
    if _is_execution_running(state):
        display.warn("another execution is running; use /status first")
        return
    state.status = SessionStatus.RUNNING
    state.active_execution_description = task_text
    state.active_execution_task = asyncio.create_task(run_task(agent, task_text, display))
    display.info("execution started in background; you can use /status and /approvals while it runs")


async def run_cli_loop(
    lines: Iterable[str],
    *,
    agent: Any,
    model: OpenRouterModelAdapter,
    display: CLIDisplay,
    mcp_state: MCPRuntimeState | None = None,
    approval_client: DirectClientChannel | None = None,
    state: CLISessionState | None = None,
    background_execute: bool = False,
) -> tuple[CLISessionState, bool]:
    """Run CLI loop over input lines. Returns (state, quit_requested)."""
    if state is None:
        state = CLISessionState()
    display.show_mode(state.mode)
    quit_requested = False

    for raw in lines:
        await _finalize_background_execution_if_done(state, display)
        command_or_task = parse_command(raw)
        if isinstance(command_or_task, Command):
            cmd = command_or_task
            if cmd.type == CommandType.QUIT:
                if _is_execution_running(state):
                    display.warn("cancelling running execution")
                    assert state.active_execution_task is not None
                    state.active_execution_task.cancel()
                    await _finalize_background_execution_if_done(state, display)
                display.info("bye")
                quit_requested = True
                break
            if cmd.type == CommandType.HELP:
                display.info(
                    "/mode [plan|execute], /approve, /reject, /status, "
                    "/approvals [list|poll|grant|deny|revoke], /mcp [list|inspect [tool_name]|reload|unload], /quit"
                )
                continue
            if cmd.type == CommandType.STATUS:
                running = _is_execution_running(state)
                display.info(f"status={state.status.value}, mode={state.mode.value}, running={running}")
                if running and state.active_execution_description:
                    display.info(f"active_task={state.active_execution_description}")
                continue
            if cmd.type == CommandType.APPROVALS:
                await _handle_approvals_command(
                    cmd.args,
                    approval_client=approval_client,
                    display=display,
                )
                continue
            if cmd.type == CommandType.MCP:
                await _handle_mcp_command(
                    cmd.args,
                    agent=agent,
                    display=display,
                    mcp_state=mcp_state,
                )
                continue
            if cmd.type == CommandType.MODE:
                if not cmd.args:
                    display.warn("/mode requires plan or execute")
                    continue
                mode = cmd.args[0].lower()
                if mode == ExecutionMode.PLAN.value:
                    state.mode = ExecutionMode.PLAN
                    display.show_mode(state.mode)
                elif mode == ExecutionMode.EXECUTE.value:
                    state.mode = ExecutionMode.EXECUTE
                    display.show_mode(state.mode)
                else:
                    display.warn("unknown mode")
                continue
            if cmd.type == CommandType.APPROVE:
                if state.pending_task_description is None:
                    display.warn("no pending plan")
                    continue
                task_text = state.pending_task_description
                _clear_pending_plan(state)
                if background_execute:
                    await _start_background_execution(
                        state=state,
                        agent=agent,
                        task_text=task_text,
                        display=display,
                    )
                else:
                    state.status = SessionStatus.RUNNING
                    await run_task(agent, task_text, display)
                    state.status = SessionStatus.IDLE
                continue
            if cmd.type == CommandType.REJECT:
                _clear_pending_plan(state)
                if not _is_execution_running(state):
                    state.status = SessionStatus.IDLE
                display.info("plan rejected")
                continue
            continue

        _, task_text = command_or_task
        if not task_text:
            continue

        if state.mode == ExecutionMode.PLAN:
            state.pending_task_description = task_text
            state.pending_plan = await preview_plan(task_text, model, display)
            state.status = SessionStatus.AWAITING_APPROVAL
            display.info("type /approve to execute or /reject to cancel")
        else:
            if background_execute:
                await _start_background_execution(
                    state=state,
                    agent=agent,
                    task_text=task_text,
                    display=display,
                )
            else:
                state.status = SessionStatus.RUNNING
                await run_task(agent, task_text, display)
                state.status = SessionStatus.IDLE

    await _finalize_background_execution_if_done(state, display)
    return (state, quit_requested)


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="DARE coding agent CLI (MCP)")
    parser.add_argument("--mode", choices=["plan", "execute"], default="execute")
    parser.add_argument("--script", type=str, default=None, help="run scripted CLI session")
    parser.add_argument("--demo", type=str, default=None, help="run demo script")
    parser.add_argument("--model", type=str, default=None, help="OpenRouter model name")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY not set")
        sys.exit(1)

    model_name = args.model or os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.7")
    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))
    timeout_seconds = float(os.getenv("OPENROUTER_TIMEOUT", "60"))
    workspace = Path(__file__).parent / "workspace"
    workspace.mkdir(exist_ok=True)

    display = CLIDisplay()
    display.header("DARE CODING AGENT + MCP")
    display.info(f"model={model_name}")
    display.info(f"workspace={workspace}")
    display.info(f"max_tokens={max_tokens}")
    display.info(f"timeout={timeout_seconds}s")

    example_dir = Path(__file__).parent
    config_provider = FileConfigProvider(
        workspace_dir=example_dir,
        user_dir=Path.home(),
    )
    config = _resolve_config_paths(config_provider.current(), example_dir)
    if config.mcp_paths:
        display.info(f"mcp_paths={config.mcp_paths}")
        display.info("MCP config found. Start local_mcp_server.py in another terminal if using local_math.")
    else:
        display.warn("No mcp_paths configured. MCP tools will not be loaded by default.")

    approval_client = DirectClientChannel()
    approval_channel = AgentChannel.build(approval_client)
    agent = await build_agent(
        workspace,
        model_name,
        api_key,
        max_tokens,
        timeout_seconds,
        display,
        config,
        agent_channel=approval_channel,
    )
    await approval_channel.start()
    mcp_state = MCPRuntimeState(
        config_provider=config_provider,
        config=config,
        config_base_dir=example_dir,
    )
    display.show_tool_lists(agent)

    model = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
        http_client_options={"timeout": timeout_seconds},
    )

    try:
        if args.demo:
            script_path = Path(args.demo)
            lines = load_script_lines(script_path)
            await run_cli_loop(
                lines,
                agent=agent,
                model=model,
                display=display,
                mcp_state=mcp_state,
                approval_client=approval_client,
            )
            return

        if args.script:
            script_path = Path(args.script)
            lines = load_script_lines(script_path)
            await run_cli_loop(
                lines,
                agent=agent,
                model=model,
                display=display,
                mcp_state=mcp_state,
                approval_client=approval_client,
            )
            return

        display.info("type /help for commands. /quit to exit.")
        cli_state = CLISessionState()
        while True:
            try:
                raw = input("dare> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not raw:
                continue
            cli_state, quit_requested = await run_cli_loop(
                [raw],
                agent=agent,
                model=model,
                display=display,
                mcp_state=mcp_state,
                approval_client=approval_client,
                state=cli_state,
                background_execute=True,
            )
            if quit_requested:
                break
    finally:
        await approval_channel.stop()


if __name__ == "__main__":
    asyncio.run(main())
