"""Interactive CLI for the DARE coding agent example.

This CLI is demo-friendly and supports both interactive and scripted runs.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import DareAgentBuilder
from dare_framework.config.types import Config
from dare_framework.context import Context, Message
from dare_framework.event.kernel import IEventLog
from dare_framework.event.types import Event, RuntimeSnapshot
from dare_framework.knowledge import RawDataKnowledge, InMemoryRawDataStorage
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.plan import DefaultPlanner, DefaultRemediator, Task
from dare_framework.tool import ReadFileTool, WriteFileTool, SearchCodeTool, RunCommandTool, RunContext

from validators.file_validator import FileExistsValidator


class CommandType(Enum):
    QUIT = "quit"
    MODE = "mode"
    APPROVE = "approve"
    REJECT = "reject"
    STATUS = "status"
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
        """打印 MCP 工具列表与本地工具列表。"""
        provider = getattr(getattr(agent, "context", None), "_tool_provider", None)
        if provider is None:
            self.info("tools: (none)")
            return
        try:
            tools = provider.list_tools()
        except Exception:
            self.info("tools: (unable to list)")
            return
        mcp = [t for t in tools if ":" in getattr(t, "name", "")]
        local = [t for t in tools if ":" not in getattr(t, "name", "")]
        names = lambda lst: [getattr(t, "name", str(t)) for t in lst]
        self.info(f"MCP tools ({len(mcp)}): {names(mcp) if mcp else []}")
        self.info(f"Local tools ({len(local)}): {names(local) if local else []}")

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
            self.info(f">>> selected tool: [{name}] (attempt {attempt})")
            return
        if event_type == "tool.result":
            name = payload.get("capability_id") or payload.get("tool") or "?"
            success = payload.get("success", True)
            if success:
                self.ok(f">>> tool result [{name}]: ok")
            else:
                self.warn(f">>> tool result [{name}]: failed")
            return
        if event_type == "tool.error":
            name = payload.get("capability_id") or payload.get("tool") or "?"
            err = payload.get("error")
            self.error(f">>> tool error [{name}]: {err}")
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


def _create_builder(
    workspace: Path,
    model_name: str,
    api_key: str,
    max_tokens: int,
    timeout_seconds: float,
    display: CLIDisplay,
    *,
    initial_skill_path: Path | str | None = None,
    config: Config | None = None,
) -> DareAgentBuilder:
    """创建 DareAgentBuilder；MCP 由 builder.build() 内部根据 config.mcp_paths 加载。"""
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

    # Rawdata knowledge (in-memory): agent can call knowledge_get / knowledge_add as tools.
    knowledge = RawDataKnowledge(storage=InMemoryRawDataStorage())

    builder = (
        DareAgentBuilder("dare-coding-agent")
        .with_model(model)
        .with_knowledge(knowledge)
        .add_tools(*tools)
        .with_run_context_factory(
            lambda: RunContext(
                metadata={"agent": "dare-coding-agent"},
                config={"workspace_roots": [str(workspace)]},
            )
        )
        .with_planner(DefaultPlanner(model, verbose=False))
        .add_validators(validator)
        .with_remediator(DefaultRemediator(model, verbose=False))
        .with_event_log(event_log)
    )
    if config is not None:
        builder = builder.with_config(config)
    if initial_skill_path:
        builder = builder.with_skill(initial_skill_path)
    return builder


async def preview_plan(task_text: str, model: OpenRouterModelAdapter, display: CLIDisplay) -> Any:
    ctx = Context(id="plan-preview")
    ctx.stm_add(Message(role="user", content=task_text))
    planner = DefaultPlanner(model, verbose=False)
    plan = await planner.plan(ctx)
    display.show_plan(plan)
    return plan


async def run_task(agent: Any, task_text: str, display: CLIDisplay) -> None:
    display.header("EXECUTION")
    result = await agent.run(Task(description=task_text))
    if result.success:
        display.ok("task completed")
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
                display.info("/mode [plan|execute], /approve, /reject, /status, /quit")
                continue
            if cmd.type == CommandType.STATUS:
                display.info(f"status={state.status.value}, mode={state.mode.value}")
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
                await run_task(agent, state.pending_task_description, display)
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
            state.pending_plan = await preview_plan(task_text, model, display)
            state.status = SessionStatus.AWAITING_APPROVAL
            display.info("type /approve to execute or /reject to cancel")
        else:
            state.status = SessionStatus.RUNNING
            await run_task(agent, task_text, display)
            state.reset_task()

    return (state, quit_requested)


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="DARE coding agent CLI")
    parser.add_argument("--mode", choices=["plan", "execute"], default="execute")
    parser.add_argument("--script", type=str, default=None, help="run scripted CLI session")
    parser.add_argument("--demo", type=str, default=None, help="run demo script")
    parser.add_argument("--model", type=str, default=None, help="OpenRouter model name")
    parser.add_argument(
        "--skill",
        type=str,
        default=None,
        help="path to initial skill directory (one skill)",
    )
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    api_key = "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"
    if not api_key:
        print("OPENROUTER_API_KEY not set")
        sys.exit(1)

    model_name = "openai/gpt-oss-120b"
    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))
    timeout_seconds = float(os.getenv("OPENROUTER_TIMEOUT", "60"))
    workspace = Path(__file__).parent / "workspace"
    workspace.mkdir(exist_ok=True)

    display = CLIDisplay()
    display.header("DARE CODING AGENT")
    display.info(f"model={model_name}")
    display.info(f"workspace={workspace}")
    display.info(f"max_tokens={max_tokens}")
    display.info(f"timeout={timeout_seconds}s")

    example_dir = Path(__file__).parent
    mcp_dir = example_dir / ".dare" / "mcp"
    config = None
    if mcp_dir.exists():
        config = Config(
            mcp_paths=[str(mcp_dir)],
            workspace_dir=str(example_dir),
            user_dir=str(Path.home()),
        )
        display.info("MCP config found. Start local_mcp_server.py in another terminal if using local_math.")

    initial_skill_path = Path(args.skill) if args.skill else None
    builder = _create_builder(
        workspace,
        model_name,
        api_key,
        max_tokens,
        timeout_seconds,
        display,
        initial_skill_path=initial_skill_path,
        config=config,
    )
    agent = await builder.build()
    display.show_tool_lists(agent)

    model = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
        http_client_options={"timeout": timeout_seconds},
    )

    if args.demo:
        script_path = Path(args.demo)
        lines = load_script_lines(script_path)
        await run_cli_loop(lines, agent=agent, model=model, display=display)
        return

    if args.script:
        script_path = Path(args.script)
        lines = load_script_lines(script_path)
        await run_cli_loop(lines, agent=agent, model=model, display=display)
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
            [raw], agent=agent, model=model, display=display, state=cli_state
        )
        if quit_requested:
            break


if __name__ == "__main__":
    asyncio.run(main())
