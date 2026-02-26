"""Minimal non-CLI ReAct loop similar to AgentScope's basic example."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, TypedDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import BaseAgent
from dare_framework.config import Config
from dare_framework.model import OpenRouterModelAdapter, Prompt
from dare_framework.model.kernel import IModelAdapter
from dare_framework.tool.kernel import ITool
from dare_framework.tool.types import CapabilityKind, RiskLevelName, RunContext, ToolResult, ToolType


class CommandOutput(TypedDict):
    stdout: str
    stderr: str
    exit_code: int


def _workspace_from_run_context(run_context: RunContext[Any]) -> Path:
    deps = run_context.deps
    if deps is not None and hasattr(deps, "config"):
        config = getattr(deps, "config", None)
        if config is not None and hasattr(config, "workspace_dir"):
            return Path(str(getattr(config, "workspace_dir"))).resolve()
    return Path.cwd().resolve()


class ExecutePythonCodeTool(ITool):
    """Execute short Python snippets inside workspace context."""

    @property
    def name(self) -> str:
        return "execute_python_code"

    @property
    def description(self) -> str:
        return "Execute python code via python -c and return stdout/stderr."

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "non_idempotent_effect"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 30

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        code: str,
        timeout_seconds: int | None = None,
    ) -> ToolResult[CommandOutput]:
        if not code.strip():
            return ToolResult(success=False, output={"stdout": "", "stderr": "", "exit_code": 1}, error="code is required")

        workspace = _workspace_from_run_context(run_context)
        timeout = timeout_seconds or self.timeout_seconds
        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                code,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_raw, stderr_raw = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            if proc is not None and proc.returncode is None:
                proc.kill()
                await proc.communicate()
            return ToolResult(
                success=False,
                output={"stdout": "", "stderr": "python execution timeout", "exit_code": 124},
                error="python execution timeout",
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                output={"stdout": "", "stderr": str(exc), "exit_code": 1},
                error=str(exc),
            )

        stdout = stdout_raw.decode("utf-8", errors="replace")
        stderr = stderr_raw.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
        return ToolResult(
            success=exit_code == 0,
            output={"stdout": stdout, "stderr": stderr, "exit_code": exit_code},
            error=None if exit_code == 0 else "python execution failed",
        )


class ExecuteShellCommandTool(ITool):
    """Execute shell command in workspace context."""

    @property
    def name(self) -> str:
        return "execute_shell_command"

    @property
    def description(self) -> str:
        return "Execute shell command and return stdout/stderr."

    @property
    def tool_type(self) -> ToolType:
        return ToolType.ATOMIC

    @property
    def risk_level(self) -> RiskLevelName:
        return "non_idempotent_effect"

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def timeout_seconds(self) -> int:
        return 30

    @property
    def is_work_unit(self) -> bool:
        return False

    @property
    def capability_kind(self) -> CapabilityKind:
        return CapabilityKind.TOOL

    async def execute(
        self,
        *,
        run_context: RunContext[Any],
        command: str,
        timeout_seconds: int | None = None,
    ) -> ToolResult[CommandOutput]:
        if not command.strip():
            return ToolResult(
                success=False,
                output={"stdout": "", "stderr": "", "exit_code": 1},
                error="command is required",
            )

        workspace = _workspace_from_run_context(run_context)
        timeout = timeout_seconds or self.timeout_seconds
        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_raw, stderr_raw = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            if proc is not None and proc.returncode is None:
                proc.kill()
                await proc.communicate()
            return ToolResult(
                success=False,
                output={"stdout": "", "stderr": "shell execution timeout", "exit_code": 124},
                error="shell execution timeout",
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                output={"stdout": "", "stderr": str(exc), "exit_code": 1},
                error=str(exc),
            )

        stdout = stdout_raw.decode("utf-8", errors="replace")
        stderr = stderr_raw.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
        return ToolResult(
            success=exit_code == 0,
            output={"stdout": stdout, "stderr": stderr, "exit_code": exit_code},
            error=None if exit_code == 0 else "shell execution failed",
        )


async def build_simple_agent(
    *,
    workspace_dir: Path,
    model_adapter: IModelAdapter,
) -> Any:
    config = Config(
        workspace_dir=str(workspace_dir),
        user_dir=str(Path.home()),
    )
    sys_prompt = Prompt(
        prompt_id="example10.friday.system",
        role="system",
        content="You're a helpful assistant named Friday.",
        supported_models=["*"],
        order=100,
    )
    return await (
        BaseAgent.react_agent_builder("Friday")
        .with_model(model_adapter)
        .with_config(config)
        .with_prompt(sys_prompt)
        .add_tools(ExecutePythonCodeTool(), ExecuteShellCommandTool())
        .build()
    )


async def run_simple_loop(
    *,
    workspace: Path,
    model_name: str,
    max_tokens: int,
    timeout_seconds: float,
) -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")

    workspace.mkdir(parents=True, exist_ok=True)
    model_adapter = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
        http_client_options={"timeout": timeout_seconds},
    )
    agent = await build_simple_agent(workspace_dir=workspace, model_adapter=model_adapter)

    msg: str | None = None
    print("Friday ready. Type your message. Type 'exit' to quit.\n", flush=True)
    while True:
        if msg is not None:
            print(f"Friday: {msg}\n", flush=True)
        user_text = (await asyncio.to_thread(input, "user> ")).strip()
        if user_text == "exit":
            break
        result = await agent(user_text)
        msg = result.output_text or str(result.output)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Example 10 minimal ReAct loop (no transport CLI)")
    parser.add_argument("--workspace", type=str, default=str(Path(__file__).parent / "workspace"))
    parser.add_argument("--model", type=str, default=os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.7"))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("OPENROUTER_MAX_TOKENS", "2048")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("OPENROUTER_TIMEOUT", "60")))
    return parser


async def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    await run_simple_loop(
        workspace=Path(args.workspace).expanduser().resolve(),
        model_name=args.model,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout,
    )


if __name__ == "__main__":
    asyncio.run(main())
