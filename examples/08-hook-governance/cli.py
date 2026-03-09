"""Interactive CLI for hook governance with a real LLM backend.

This example mirrors the real-LLM style from 05 while keeping the flow small.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import BaseAgent
from dare_framework.config import Config
from dare_framework.context import Message
from dare_framework.hook.kernel import IHook
from dare_framework.hook.types import HookDecision, HookPhase, HookResult
from dare_framework.infra.component import ComponentType
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.model.types import ModelInput
from dare_framework.tool._internal.tools import ReadFileTool, SearchCodeTool, WriteFileTool


class CommandType(Enum):
    QUIT = "quit"
    HELP = "help"
    STATS = "stats"


@dataclass
class Command:
    type: CommandType
    raw_input: str


def parse_command(user_input: str) -> Command | tuple[None, str]:
    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return (None, stripped)

    cmd = stripped[1:].split(maxsplit=1)[0].lower()
    mapping = {
        "quit": CommandType.QUIT,
        "exit": CommandType.QUIT,
        "q": CommandType.QUIT,
        "help": CommandType.HELP,
        "stats": CommandType.STATS,
    }
    if cmd not in mapping:
        return (None, stripped)
    return Command(type=mapping[cmd], raw_input=user_input)


class GovernancePolicyHook(IHook):
    """Governance hook with visible patch/block behavior in CLI."""

    def __init__(self, *, block_keyword: str = "#hook_block_model") -> None:
        self._block_keyword = block_keyword
        self.phase_counts: Counter[str] = Counter()
        self.patch_applied_count = 0
        self.blocked_model_count = 0
        self.blocked_tool_count = 0
        self.tool_seen_count = 0
        self.last_tool_name: str | None = None
        self.last_user_before_patch: str | None = None
        self.last_user_after_patch: str | None = None

    @property
    def name(self) -> str:
        return "governance-policy-hook"

    @property
    def component_type(self) -> Literal[ComponentType.HOOK]:
        return ComponentType.HOOK

    async def invoke(self, phase: HookPhase, *args: Any, **kwargs: Any) -> HookResult:
        _ = args
        self.phase_counts[phase.value] += 1
        payload = kwargs.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}

        if phase is HookPhase.BEFORE_MODEL:
            model_input = payload.get("model_input")
            if isinstance(model_input, ModelInput):
                first_user = _first_user_message(model_input.messages)
                if first_user is not None and self._block_keyword in first_user:
                    self.blocked_model_count += 1
                    print(f"[HOOK] BEFORE_MODEL -> BLOCK (matched keyword: {self._block_keyword})", flush=True)
                    return HookResult(
                        decision=HookDecision.BLOCK,
                        message=f"model blocked by hook keyword {self._block_keyword}",
                    )
                patched = _patch_model_input(model_input)
                if patched is not None:
                    self.patch_applied_count += 1
                    self.last_user_before_patch = first_user
                    self.last_user_after_patch = _first_user_message(patched.messages)
                    print("[HOOK] BEFORE_MODEL -> PATCH model_input", flush=True)
                    return HookResult(
                        decision=HookDecision.ALLOW,
                        patch={"model_input": patched},
                        message="model_input patched",
                    )

        if phase is HookPhase.BEFORE_TOOL:
            tool_name = str(payload.get("tool_name", ""))
            self.tool_seen_count += 1
            self.last_tool_name = tool_name or "<unknown>"
            # Demonstrate governance control on high-impact local writes.
            if tool_name == "write_file":
                self.blocked_tool_count += 1
                print("[HOOK] BEFORE_TOOL -> BLOCK write_file", flush=True)
                return HookResult(
                    decision=HookDecision.BLOCK,
                    message="write_file denied by hook policy in this example",
                )
            print(f"[HOOK] BEFORE_TOOL -> ALLOW {self.last_tool_name}", flush=True)

        return HookResult(decision=HookDecision.ALLOW)


def _first_user_message(messages: list[Message]) -> str | None:
    for message in messages:
        if message.role == "user":
            return message.text
    return None


def _patch_model_input(model_input: ModelInput) -> ModelInput | None:
    patched = False
    patched_messages: list[Message] = []
    for message in model_input.messages:
        if not patched and message.role == "user":
            content = message.text or ""
            if not content.startswith("[hook patched]"):
                content = f"[hook patched] {content}"
            patched_messages.append(
                Message(
                    role=message.role,
                    text=content,
                    name=message.name,
                    metadata=dict(message.metadata),
                )
            )
            patched = True
            continue
        patched_messages.append(message)

    if not patched:
        return None

    patched_metadata = dict(model_input.metadata)
    patched_metadata["model_input_patch_applied"] = True
    return ModelInput(
        messages=patched_messages,
        tools=list(model_input.tools),
        metadata=patched_metadata,
    )


def _format_result_output(output: Any) -> str:
    if isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, str):
            return content
        return str(output)
    if output is None:
        return ""
    return str(output)


def _print_help() -> None:
    print("\nCommands:", flush=True)
    print("  /help   Show help", flush=True)
    print("  /stats  Show hook governance stats", flush=True)
    print("  /quit   Exit", flush=True)
    print("\nTips:", flush=True)
    print("  - Normal task: observe BEFORE_MODEL patch logs.", flush=True)
    print("  - Include '#hook_block_model' in prompt to trigger BEFORE_MODEL block.", flush=True)
    print("  - Ask to write files to observe BEFORE_TOOL block for write_file.", flush=True)


def _print_stats(hook: GovernancePolicyHook) -> None:
    print("\nHook stats:", flush=True)
    print(f"  patch_applied_count={hook.patch_applied_count}", flush=True)
    print(f"  blocked_model_count={hook.blocked_model_count}", flush=True)
    print(f"  blocked_tool_count={hook.blocked_tool_count}", flush=True)
    print(f"  tool_seen_count={hook.tool_seen_count}", flush=True)
    if hook.last_tool_name is not None:
        print(f"  last_tool_name={hook.last_tool_name}", flush=True)
    if hook.last_user_before_patch is not None:
        print(f"  last_user_before_patch={hook.last_user_before_patch}", flush=True)
    if hook.last_user_after_patch is not None:
        print(f"  last_user_after_patch={hook.last_user_after_patch}", flush=True)
    print("  phase_counts:", flush=True)
    for phase_name in sorted(hook.phase_counts):
        print(f"    {phase_name}: {hook.phase_counts[phase_name]}", flush=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hook governance CLI with real LLM.")
    parser.add_argument(
        "--workspace",
        default=str(Path.cwd()),
        help="Workspace directory for file tools.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.7"),
        help="OpenRouter model name.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.getenv("OPENROUTER_MAX_TOKENS", "2048")),
        help="Max tokens passed to model adapter.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("OPENROUTER_TIMEOUT", "60")),
        help="HTTP timeout seconds for model calls.",
    )
    return parser


async def _build_agent(
    *,
    workspace: Path,
    model_name: str,
    api_key: str,
    max_tokens: int,
    timeout_seconds: float,
    hook: GovernancePolicyHook,
) -> Any:
    workspace.mkdir(parents=True, exist_ok=True)

    model = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
        http_client_options={"timeout": timeout_seconds},
    )
    config = Config(
        workspace_dir=str(workspace),
        user_dir=str(Path.home()),
    )
    return await (
        BaseAgent.dare_agent_builder("hook-governance-cli")
        .with_model(model)
        .with_config(config)
        .add_tools(ReadFileTool(), WriteFileTool(), SearchCodeTool())
        .add_hooks(hook)
        .build()
    )


async def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set", flush=True)
        raise SystemExit(1)

    hook = GovernancePolicyHook()
    agent = await _build_agent(
        workspace=Path(args.workspace),
        model_name=args.model,
        api_key=api_key,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout,
        hook=hook,
    )

    print(f"Hook governance CLI ready (model: {args.model})", flush=True)
    print(f"Workspace: {args.workspace}", flush=True)
    _print_help()

    while True:
        try:
            raw = input("\nhook> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.", flush=True)
            return

        if not raw:
            continue

        parsed = parse_command(raw)
        if isinstance(parsed, Command):
            if parsed.type is CommandType.QUIT:
                print("Bye.", flush=True)
                return
            if parsed.type is CommandType.HELP:
                _print_help()
                continue
            if parsed.type is CommandType.STATS:
                _print_stats(hook)
                continue

        task_text = parsed[1] if isinstance(parsed, tuple) else raw
        result = await agent(task_text)
        output_text = _format_result_output(result.output)
        print(f"\nAssistant: {output_text}", flush=True)
        if result.errors:
            print(f"Errors: {result.errors}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
