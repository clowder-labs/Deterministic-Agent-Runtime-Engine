"""Interactive CLI for the DARE coding agent example.

This CLI is demo-friendly and supports both interactive and scripted runs.
"""
from __future__ import annotations

import ast
import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import DareAgentBuilder
from dare_framework.config import Config
from dare_framework.context import Context, Message
from dare_framework.event.kernel import IEventLog
from dare_framework.event.types import Event, RuntimeSnapshot
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.plan import DefaultPlanner, DefaultRemediator, Task
from dare_framework.tool.action_handler import ApprovalsActionHandler
from dare_framework.tool._internal.control.approval_manager import (
    ApprovalMatcherKind,
    ApprovalScope,
    ToolApprovalManager,
)
from dare_framework.tool._internal.tools import ReadFileTool, RunCommandTool, SearchCodeTool, WriteFileTool
from dare_framework.transport.interaction.resource_action import ResourceAction

from validators.file_validator import FileExistsValidator


class CommandType(Enum):
    QUIT = "quit"
    MODE = "mode"
    APPROVE = "approve"
    REJECT = "reject"
    STATUS = "status"
    APPROVALS = "approvals"
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
    conversation_id: str = field(default_factory=lambda: uuid4().hex)

    def reset_task(self) -> None:
        self.status = SessionStatus.IDLE
        self.pending_plan = None
        self.pending_task_description = None


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
        if event_type == "exec.waiting_human":
            checkpoint_id = payload.get("checkpoint_id", "?")
            reason = payload.get("reason")
            self.warn(f"waiting for approval: request_id={checkpoint_id}")
            if reason:
                self.info(f"approval reason: {reason}")
            self.info("approve now: y=once allow, a=allow+remember(workspace), n=deny")
            return
        if event_type == "tool.approval":
            status = payload.get("status")
            source = payload.get("source")
            self.info(f"tool approval: status={status}, source={source}")
            return
        if event_type == "tool.invoke":
            name = payload.get("capability_id")
            attempt = payload.get("attempt")
            self.info(f"tool invoke: {name} (attempt {attempt})")
            return
        if event_type == "tool.result":
            name = payload.get("capability_id")
            self.ok(f"tool result: {name}")
            return
        if event_type == "tool.error":
            name = payload.get("capability_id")
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
    def __init__(
        self,
        on_event: callable,
        *,
        approval_manager: ToolApprovalManager | None = None,
        prompt_fn: callable | None = None,
    ) -> None:
        self._on_event = on_event
        self._approval_manager = approval_manager
        self._prompt_fn = prompt_fn or input
        self._events: list[Event] = []

    async def append(self, event_type: str, payload: dict[str, Any]) -> str:
        self._on_event(event_type, payload)
        if event_type == "exec.waiting_human":
            await self._resolve_pending_approval(payload)
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

    async def _resolve_pending_approval(self, payload: dict[str, Any]) -> None:
        if self._approval_manager is None:
            return
        request_id = payload.get("checkpoint_id")
        if not isinstance(request_id, str) or not request_id:
            return
        choice = await self._prompt_approval_choice(request_id=request_id)
        if choice == "allow_workspace":
            await self._approval_manager.grant(
                request_id,
                scope=ApprovalScope.WORKSPACE,
                matcher=ApprovalMatcherKind.EXACT_PARAMS,
            )
            return
        if choice == "allow_once":
            await self._approval_manager.grant(
                request_id,
                scope=ApprovalScope.ONCE,
                matcher=ApprovalMatcherKind.EXACT_PARAMS,
            )
            return
        await self._approval_manager.deny(
            request_id,
            scope=ApprovalScope.ONCE,
            matcher=ApprovalMatcherKind.EXACT_PARAMS,
        )

    async def _prompt_approval_choice(self, *, request_id: str) -> str:
        prompt = (
            f"[APPROVAL] request_id={request_id} "
            "(y=allow once / a=allow+remember workspace / n=deny): "
        )
        loop = asyncio.get_running_loop()
        try:
            raw = await loop.run_in_executor(None, self._prompt_fn, prompt)
        except Exception:
            return "deny"
        value = str(raw or "").strip().lower()
        if value in {"y", "yes", "allow"}:
            return "allow_once"
        if value in {"a", "always", "workspace"}:
            return "allow_workspace"
        return "deny"


def _match_filter(event: Event, filter: dict[str, Any]) -> bool:
    for key, value in filter.items():
        if event.payload.get(key) != value:
            return False
    return True


def _approvals_usage(display: CLIDisplay) -> None:
    display.info("/approvals list")
    display.info("/approvals poll [timeout_ms=30000]")
    display.info("/approvals grant <request_id> [scope=workspace] [matcher=exact_params] [matcher_value=...]")
    display.info("/approvals deny <request_id> [scope=once] [matcher=exact_params] [matcher_value=...]")
    display.info("/approvals revoke <rule_id>")


def _resolve_approvals_handler(agent: Any) -> ApprovalsActionHandler | None:
    approval_manager = getattr(agent, "_approval_manager", None)
    if approval_manager is None:
        return None
    return ApprovalsActionHandler(approval_manager)


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


async def _handle_approvals_command(
    args: list[str],
    *,
    agent: Any,
    display: CLIDisplay,
) -> None:
    handler = _resolve_approvals_handler(agent)
    if handler is None:
        display.warn("approval manager unavailable on current agent")
        return
    if not args:
        _approvals_usage(display)
        return

    subcommand = args[0].lower()
    try:
        if subcommand == "list":
            result = await handler.invoke(ResourceAction.APPROVALS_LIST)
            pending = result.get("pending", [])
            rules = result.get("rules", [])
            display.info(f"pending={len(pending)} rules={len(rules)}")
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            return

        if subcommand == "poll":
            _positional, options = _parse_key_value_args(args[1:])
            params: dict[str, Any] = {}
            for key in ("timeout_ms", "timeout_seconds"):
                if key in options and options[key]:
                    params[key] = options[key]
            result = await handler.invoke(ResourceAction.APPROVALS_POLL, **params)
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
            result = await handler.invoke(action, **params)
            display.ok(f"{subcommand} applied: {request_id}")
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            return

        if subcommand == "revoke":
            if len(args) < 2:
                display.warn("/approvals revoke requires rule_id")
                _approvals_usage(display)
                return
            rule_id = args[1]
            result = await handler.invoke(
                ResourceAction.APPROVALS_REVOKE,
                rule_id=rule_id,
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


async def build_agent(
    workspace: Path,
    model_name: str,
    api_key: str,
    max_tokens: int,
    timeout_seconds: float,
    display: CLIDisplay,
) -> Any:
    model = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
        http_client_options={"timeout": timeout_seconds},
    )
    tools = [ReadFileTool(), WriteFileTool(), SearchCodeTool(), RunCommandTool()]
    # expected_files=[]：不强制检查某文件，仅按执行是否成功验证，避免“创建 helloworld.py”等任务因缺少 snake_game.py 而一直重试
    validator = FileExistsValidator(
        workspace=workspace,
        expected_files=[],
        verbose=False,
    )

    approval_manager = ToolApprovalManager.from_paths(
        workspace_dir=workspace,
        user_dir=Path.home(),
    )
    event_log = StreamingEventLog(
        display.show_event,
        approval_manager=approval_manager,
    )
    agent_config = Config(
        workspace_dir=str(workspace),
        user_dir=str(Path.home()),
    )

    agent = await (
        DareAgentBuilder("dare-coding-agent")
        .with_model(model)
        .with_config(agent_config)
        .add_tools(*tools)
        .with_planner(DefaultPlanner(model, verbose=False))
        .add_validators(validator)
        .with_remediator(DefaultRemediator(model, verbose=False))
        .with_approval_manager(approval_manager)
        .with_event_log(event_log)
        .build()
    )

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


def _try_parse_serialized_container(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped:
        return None
    if not (
        (stripped.startswith("[") and stripped.endswith("]"))
        or (stripped.startswith("{") and stripped.endswith("}"))
    ):
        return None

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(stripped)
        except Exception:
            continue
        if isinstance(parsed, (list, dict)):
            return parsed
    return None


def _extract_text_payload(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        if not value.strip():
            return None
        # Some models return serialized list/dict text; parse and normalize it.
        parsed = _try_parse_serialized_container(value)
        if parsed is not None:
            parsed_text = _extract_text_payload(parsed)
            if parsed_text:
                return parsed_text
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            part = _extract_text_payload(item)
            if part:
                parts.append(part)
        if not parts:
            return None
        merged = "".join(parts)
        return merged if merged.strip() else None
    if isinstance(value, dict):
        for key in ("content", "text", "output", "message", "result"):
            if key in value:
                extracted = _extract_text_payload(value.get(key))
                if extracted:
                    return extracted
        return None
    text = str(value).strip()
    return text or None


def _format_result_output(output: Any) -> str | None:
    """Extract displayable text from RunResult.output."""
    text = _extract_text_payload(output)
    if text:
        return text
    if isinstance(output, dict):
        try:
            return json.dumps(output, ensure_ascii=False, indent=2)
        except TypeError:
            pass
    normalized = str(output).strip()
    return normalized or None


async def run_task(
    agent: Any,
    task_text: str,
    display: CLIDisplay,
    *,
    conversation_id: str | None = None,
) -> None:
    display.header("EXECUTION")
    metadata: dict[str, Any] = {}
    if isinstance(conversation_id, str) and conversation_id.strip():
        metadata["conversation_id"] = conversation_id.strip()
    try:
        result = await agent(Task(description=task_text, metadata=metadata))
    except Exception as exc:
        display.error(f"execution error: {exc}")
        return

    if result.success:
        display.ok("task completed")
        # Some tasks only produce natural-language output; print it explicitly.
        reply = _format_result_output(result.output)
        if reply:
            print("\n--- result ---\n", flush=True)
            print(reply, flush=True)
            print(flush=True)
    else:
        display.error("task failed")
        if result.errors:
            display.error(f"errors: {result.errors}")


async def run_cli_loop(
    lines: Iterable[str],
    *,
    agent: Any,
    model: OpenRouterModelAdapter,
    display: CLIDisplay,
    state: CLISessionState | None = None,
) -> tuple[CLISessionState, bool]:
    """Run CLI loop over input lines. Returns (state, quit_requested)."""
    if state is None:
        state = CLISessionState()
    display.show_mode(state.mode)
    quit_requested = False

    for raw in lines:
        command_or_task = parse_command(raw)
        if isinstance(command_or_task, Command):
            cmd = command_or_task
            if cmd.type == CommandType.QUIT:
                display.info("bye")
                quit_requested = True
                break
            if cmd.type == CommandType.HELP:
                display.info("/mode [plan|execute], /approve, /reject, /status, /approvals [list|poll|grant|deny|revoke], /quit")
                continue
            if cmd.type == CommandType.STATUS:
                display.info(f"status={state.status.value}, mode={state.mode.value}")
                continue
            if cmd.type == CommandType.APPROVALS:
                await _handle_approvals_command(cmd.args, agent=agent, display=display)
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
                state.status = SessionStatus.RUNNING
                await run_task(
                    agent,
                    state.pending_task_description,
                    display,
                    conversation_id=state.conversation_id,
                )
                state.reset_task()
                continue
            if cmd.type == CommandType.REJECT:
                state.reset_task()
                display.info("plan rejected")
                continue
            continue

        _, task_text = command_or_task
        if not task_text:
            continue

        if state.mode == ExecutionMode.PLAN:
            state.pending_task_description = task_text
            try:
                state.pending_plan = await preview_plan(task_text, model, display)
            except Exception as exc:
                state.reset_task()
                display.error(f"plan preview failed: {exc}")
                continue
            state.status = SessionStatus.AWAITING_APPROVAL
            display.info("type /approve to execute or /reject to cancel")
        else:
            state.status = SessionStatus.RUNNING
            await run_task(
                agent,
                task_text,
                display,
                conversation_id=state.conversation_id,
            )
            state.reset_task()

    return (state, quit_requested)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DARE coding agent CLI")
    parser.add_argument("--mode", choices=["plan", "execute"], default="execute")
    parser.add_argument("--script", type=str, default=None, help="run scripted CLI session")
    parser.add_argument("--demo", type=str, default=None, help="run demo script")
    parser.add_argument("--model", type=str, default=None, help="OpenRouter model name")
    parser.add_argument(
        "--conversation-id",
        type=str,
        default=None,
        help="Stable conversation id used to group multi-turn traces.",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default=str(Path.cwd()),
        help="Workspace root for file tools (default: current directory).",
    )
    return parser


def _resolve_conversation_id(raw: str | None) -> str:
    if isinstance(raw, str):
        normalized = raw.strip()
        if normalized:
            return normalized
    return uuid4().hex


async def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
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
    conversation_id = _resolve_conversation_id(args.conversation_id)
    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    display = CLIDisplay()
    display.header("DARE CODING AGENT")
    display.info(f"model={model_name}")
    display.info(f"workspace={workspace}")
    display.info(f"max_tokens={max_tokens}")
    display.info(f"timeout={timeout_seconds}s")
    display.info(f"conversation_id={conversation_id}")

    model = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
        http_client_options={"timeout": timeout_seconds},
    )
    agent = await build_agent(workspace, model_name, api_key, max_tokens, timeout_seconds, display)

    if args.demo:
        script_path = Path(args.demo)
        lines = load_script_lines(script_path)
        await run_cli_loop(
            lines,
            agent=agent,
            model=model,
            display=display,
            state=CLISessionState(conversation_id=conversation_id),
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
            state=CLISessionState(conversation_id=conversation_id),
        )
        return

    display.info("type /help for commands. /quit to exit.")
    cli_state = CLISessionState(conversation_id=conversation_id)
    while True:
        try:
            raw = input("dare> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            continue
        cli_state, quit_requested = await run_cli_loop(
            [raw], agent=agent, model=model, display=display, state=cli_state
        )
        if quit_requested:
            break


if __name__ == "__main__":
    asyncio.run(main())
