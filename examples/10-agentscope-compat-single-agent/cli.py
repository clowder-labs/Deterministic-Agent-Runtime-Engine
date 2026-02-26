"""Transport-driven CLI for Example 10 AgentScope compatibility demo."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
EXAMPLE_DIR = Path(__file__).resolve().parent
if str(EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_DIR))

from compat_agent import DemoBundle, build_single_agent_demo
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.transport import AgentChannel, DirectClientChannel, EnvelopeKind, TransportEnvelope, new_envelope_id


class CommandType(Enum):
    HELP = "help"
    STATUS = "status"
    SAVE = "save"
    LOAD = "load"
    QUIT = "quit"


@dataclass
class Command:
    type: CommandType
    args: list[str]
    raw_input: str


def parse_command(user_input: str) -> Command | tuple[None, str]:
    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return (None, stripped)

    parts = stripped[1:].split(maxsplit=1)
    cmd_name = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []
    command_map = {
        "help": CommandType.HELP,
        "status": CommandType.STATUS,
        "save": CommandType.SAVE,
        "load": CommandType.LOAD,
        "quit": CommandType.QUIT,
        "exit": CommandType.QUIT,
        "q": CommandType.QUIT,
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


def _new_prompt_envelope(prompt: str) -> TransportEnvelope:
    return TransportEnvelope(
        id=new_envelope_id(),
        kind=EnvelopeKind.MESSAGE,
        payload=prompt,
    )


def _session_path(workspace: Path, *, session_id: str, user_id: str) -> Path:
    return workspace / "sessions" / f"{user_id}_{session_id}.json"


def _render_output_text(output: object) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, str):
            return content
        return json.dumps(output, ensure_ascii=False)
    if output is None:
        return ""
    return str(output)


def _parse_response(response: TransportEnvelope) -> tuple[bool, str]:
    payload = response.payload
    if not isinstance(payload, dict):
        return (False, _render_output_text(payload))
    if payload.get("type") == "error":
        reason = payload.get("reason") or payload.get("error") or "unknown transport error"
        return (False, str(reason))

    # BaseAgent transport replies keep execution fields in `resp`, while legacy
    # callers may still rely on top-level fallbacks.
    resp = payload.get("resp")
    if isinstance(resp, dict):
        success = bool(resp.get("success", payload.get("success", True)))
        output = resp.get("output", payload.get("output"))
        errors = resp.get("errors", payload.get("errors", []))
        text = _render_output_text(output)
        if not success and errors:
            text = f"{text}\nerrors={errors}" if text else f"errors={errors}"
        return (success, text)

    success = bool(payload.get("success", payload.get("ok", True)))
    return (success, _render_output_text(payload.get("output")))


def _print_help() -> None:
    print("\nCommands:", flush=True)
    print("  /help              Show help", flush=True)
    print("  /status            Show current agent status", flush=True)
    print("  /save [session_id] Save context + plan notebook snapshot", flush=True)
    print("  /load [session_id] Load context + plan notebook snapshot", flush=True)
    print("  /quit              Exit", flush=True)


async def _run_task(
    *,
    client: DirectClientChannel,
    task: str,
    timeout: float,
) -> None:
    response = await client.ask(_new_prompt_envelope(task), timeout=timeout)
    success, text = _parse_response(response)
    prefix = "[OK]" if success else "[ERR]"
    print(f"{prefix} {text}", flush=True)


async def run_cli_loop(
    lines: Iterable[str],
    *,
    bundle: DemoBundle,
    client: DirectClientChannel,
    workspace: Path,
    timeout: float,
    default_session_id: str,
    user_id: str,
) -> bool:
    for raw in lines:
        command_or_task = parse_command(raw)
        if isinstance(command_or_task, Command):
            command = command_or_task
            if command.type == CommandType.QUIT:
                print("[INFO] bye", flush=True)
                return True
            if command.type == CommandType.HELP:
                _print_help()
                continue
            if command.type == CommandType.STATUS:
                print(f"[INFO] status={bundle.agent.get_status().value}", flush=True)
                continue
            if command.type == CommandType.SAVE:
                session_id = command.args[0] if command.args else default_session_id
                bundle.session.save_session_state(
                    session_id=session_id,
                    context=bundle.agent.context,
                    notebook=bundle.notebook,
                    user_id=user_id,
                )
                path = _session_path(workspace, session_id=session_id, user_id=user_id)
                print(f"[OK] session saved: {path}", flush=True)
                continue
            if command.type == CommandType.LOAD:
                session_id = command.args[0] if command.args else default_session_id
                bundle.session.load_session_state(
                    session_id=session_id,
                    context=bundle.agent.context,
                    notebook=bundle.notebook,
                    user_id=user_id,
                    allow_not_exist=False,
                )
                path = _session_path(workspace, session_id=session_id, user_id=user_id)
                print(f"[OK] session loaded: {path}", flush=True)
                continue
            continue

        _, task = command_or_task
        if not task:
            continue
        await _run_task(client=client, task=task, timeout=timeout)
    return False


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Example 10 AgentScope compatibility CLI")
    parser.add_argument("--workspace", type=str, default=str(EXAMPLE_DIR / "workspace"))
    parser.add_argument("--max-prompt-chars", type=int, default=320)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.7"),
        help="OpenRouter model name",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.getenv("OPENROUTER_MAX_TOKENS", "2048")),
        help="max tokens for OpenRouter calls",
    )
    parser.add_argument("--script", type=str, default=None, help="run scripted CLI session")
    parser.add_argument("--task", type=str, default=None, help="run one task and exit")
    parser.add_argument("--session-id", type=str, default="example-10")
    parser.add_argument("--user-id", type=str, default="demo")
    return parser


async def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")
    model_adapter = OpenRouterModelAdapter(
        model=args.model,
        api_key=api_key,
        extra={"max_tokens": args.max_tokens},
        http_client_options={"timeout": args.timeout},
    )

    client_channel = DirectClientChannel()
    channel = AgentChannel.build(client_channel)
    bundle = await build_single_agent_demo(
        workspace_dir=workspace,
        max_prompt_chars=args.max_prompt_chars,
        agent_channel=channel,
        model_adapter=model_adapter,
    )

    await bundle.agent.start()
    try:
        print("AgentScope-compat demo CLI ready.", flush=True)
        print(f"workspace={workspace}", flush=True)
        print(f"model={args.model}", flush=True)

        if args.task:
            await run_cli_loop(
                [args.task],
                bundle=bundle,
                client=client_channel,
                workspace=workspace,
                timeout=args.timeout,
                default_session_id=args.session_id,
                user_id=args.user_id,
            )
            return

        if args.script:
            lines = load_script_lines(Path(args.script))
            await run_cli_loop(
                lines,
                bundle=bundle,
                client=client_channel,
                workspace=workspace,
                timeout=args.timeout,
                default_session_id=args.session_id,
                user_id=args.user_id,
            )
            return

        print("type /help for commands. /quit to exit.", flush=True)
        while True:
            try:
                raw = input("compat> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("", flush=True)
                break
            if not raw:
                continue
            quit_requested = await run_cli_loop(
                [raw],
                bundle=bundle,
                client=client_channel,
                workspace=workspace,
                timeout=args.timeout,
                default_session_id=args.session_id,
                user_id=args.user_id,
            )
            if quit_requested:
                break
    finally:
        await bundle.agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
