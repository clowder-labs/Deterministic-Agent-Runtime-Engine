from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import replace
from datetime import datetime
from enum import Enum
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import BaseAgent
from dare_framework.config import Config
from dare_framework.skill._internal.filesystem_skill_loader import FileSystemSkillLoader
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.model.types import Prompt
from dare_framework.plan_v2 import (
    PLAN_AGENT_SYSTEM_PROMPT,
    SUB_AGENT_TASK_PROMPT,
    Planner,
    PlannerState,
    SubAgentRegistry,
)
from dare_framework.checkpoint import AgentStateCheckpointer
from dare_framework.tool._internal.tools import (
    EditLineTool,
    ReadFileTool,
    RunCommandTool,
    SearchCodeTool,
    SearchFileTool,
    WriteFileTool,
)


def _parse_args() -> argparse.Namespace:
    """解析命令行：目标工程路径。"""
    parser = argparse.ArgumentParser(
        description="对标 Claude Code：项目级 AI 编程助手。支持深度理解、修改代码、执行命令。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python plan_claude_code.py
""",
    )
    parser.add_argument(
        "project",
        nargs="?",
        default=".",
        help="目标工程路径（默认当前目录）",
    )
    return parser.parse_args()


class CommandType(Enum):
    QUIT = "quit"
    HELP = "help"


def _parse_command(user_input: str) -> CommandType | tuple[None, str]:
    """解析 / 开头的命令，否则返回 (None, 原始输入)。"""
    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return (None, stripped)
    cmd = stripped[1:].split(maxsplit=1)[0].lower()
    mapping = {
        "quit": CommandType.QUIT, "exit": CommandType.QUIT, "q": CommandType.QUIT,
        "help": CommandType.HELP,
    }
    if cmd not in mapping:
        return (None, stripped)  # 未知 / 命令当作普通输入
    return mapping[cmd]


def _print_help(project_path: str) -> None:
    print("\nCommands: /help  /quit", flush=True)
    print("\n任务类型:", flush=True)
    print("  - 理解项目、回答问题、修改代码、运行测试", flush=True)
    print(f"\n目标工程: {project_path}", flush=True)


def _reset_plan_state(state: PlannerState) -> None:
    """每轮新对话前重置 plan 状态，避免上一轮计划干扰。"""
    state.plan_description = ""
    state.steps.clear()
    state.completed_step_ids.clear()
    state.plan_validated = False
    state.plan_success = True
    state.plan_errors.clear()
    state.last_verify_errors.clear()
    state.last_remediation_summary = ""
    state.critical_block = ""


def _build_plan_prompt(workspace_dir: str, project_path: str) -> str:
    """构建主 Agent prompt（意图驱动），注入路径与 sub-agent 说明。"""
    return PLAN_AGENT_SYSTEM_PROMPT + f"""

【路径根目录】
- 目标工程目录: {project_path}
- 产出内容目录: {workspace_dir}

【可用 sub-agent】委托格式见上方【委托原则】。
- sub_agent_recon：侦察。理解代码、回答问题、搜索、生成报告（可写 workspace）。
- sub_agent_coder：可读写。创建/修改代码、添加功能、修复 bug、重构。
- sub_agent_runner：可执行。运行测试、构建、执行命令。

任务类型与 sub-agent 对应：
- 理解项目、回答问题、代码侦查 → sub_agent_recon
- 添加功能、修复 bug、写代码 → sub_agent_recon 先理解 → sub_agent_coder 实现
- 运行测试、构建 → sub_agent_runner"""


def _ensure_run_alias(agent: BaseAgent) -> BaseAgent:
    """SubAgentRegistry 需要 agent.run()，BaseAgent 仅有 __call__。添加 run 别名。"""
    if not hasattr(agent, "run") or not callable(getattr(agent, "run", None)):
        agent.run = agent.__call__  # type: ignore[method-assign]
    return agent


async def main() -> None:
    # 路径约定（简化版，只有一个 workspace_dir）：
    # - workspace_dir = D:\Agent 作为工具沙箱根目录
    # - 目标工程目录 project_path_abs = 绝对路径（只读）
    # - 交付产物目录 output_dir_abs = 绝对路径（可写）
    #
    # 所有工具调用一律使用绝对路径，由调用者自行区分「读项目」和「写产物」。

    project_path_abs = "D:\\Agent\\realesrgan\\Real-ESRGAN\\realesrgan\\archs"
    output_dir_abs = "D:\\Agent\\realesrgan\\Real-ESRGAN\\realesrgan\\dare"
    workspace_dir_abs = "D:\\Agent\\realesrgan\\Real-ESRGAN\\realesrgan"  # 工具沙箱根目录，必须同时包含 project / output

    Path(output_dir_abs).mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("OPENROUTER_API_KEY", "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")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)

    model_name = os.getenv("OPENROUTER_MODEL", "moonshotai/kimi-k2.5")
    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "4096"))

    model = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={
            "max_tokens": max_tokens,
            "temperature": 0.5,  # Agent 场景常用：工具调用稳定，表述略有变化
            "seed": 42,  # 提高 function call 一致性
        },
    )

    # 单一 workspace_dir，所有工具只检查「路径是否在 workspace_dir_abs 之下」
    base_config = Config(
        workspace_dir=workspace_dir_abs,
        user_dir=str(Path.home()),
    )
    checkpointer = AgentStateCheckpointer(user_dir=base_config.user_dir)

    def _build_sub_prompt() -> str:
        return SUB_AGENT_TASK_PROMPT

    sub_prompt = Prompt(
        prompt_id="sub-agent.system",
        role="system",
        content=_build_sub_prompt(),
        supported_models=[],
        order=0,
    )

    # sub_agent_recon：只读 + write_file，加载 code-recon skill
    _code_recon_skill_dir = Path(
        "D:\\Agent\\darev0.1\\Deterministic-Agent-Runtime-Engine\\examples\\10-react-agent-code-recon\\skills\\code-recon"
    )
    _code_recon_skills = FileSystemSkillLoader(_code_recon_skill_dir).load()
    _code_recon_skill = _code_recon_skills[0] if _code_recon_skills else None

    recon_agent = await (
        BaseAgent.react_agent_builder("sub_agent_recon")
        .with_model(model)
        .with_config(base_config)
        .with_context_strategy("basic")
        .with_prompt(sub_prompt)
        .with_sys_skill(_code_recon_skill)
        .with_skill_tool(False)  # 使用固定 code-recon skill，不启用 search_skill
        .add_tools(ReadFileTool(), SearchCodeTool(), SearchFileTool(), WriteFileTool())
        .with_max_tool_rounds(80)
        .build()
    )
    _ensure_run_alias(recon_agent)

    # sub_agent_coder：可写
    coder_agent = await (
        BaseAgent.react_agent_builder("sub_agent_coder")
        .with_model(model)
        .with_config(base_config)
        .with_context_strategy("basic")
        .with_prompt(sub_prompt)
        .add_tools(ReadFileTool(), WriteFileTool(), SearchCodeTool(), EditLineTool())
        .build()
    )
    _ensure_run_alias(coder_agent)

    # sub_agent_runner：可执行
    runner_agent = await (
        BaseAgent.react_agent_builder("sub_agent_runner")
        .with_model(model)
        .with_config(base_config)
        .with_context_strategy("basic")
        .with_prompt(sub_prompt)
        .add_tools(RunCommandTool(), ReadFileTool())
        .build()
    )
    _ensure_run_alias(runner_agent)

    registry = SubAgentRegistry()
    registry.register(
        "sub_agent_recon",
        "侦察：理解代码、回答问题、搜索、生成报告（产出到 workspace）。task 只写任务目标、交付件、目标路径。",
        lambda: recon_agent,
    )
    registry.register(
        "sub_agent_coder",
        "代码编写：read_file、write_file、search_code、edit_line。用于创建或修改代码文件。",
        lambda: coder_agent,
    )
    registry.register(
        "sub_agent_runner",
        "命令执行：run_command、read_file。用于运行测试、构建等。",
        lambda: runner_agent,
    )

    state = PlannerState(task_id="plan-claude-code-1", session_id="plan-claude-code-session-1")
    planner = Planner(state, sub_agent_registry=registry, plan_tools=False)

    plan_prompt = Prompt(
        prompt_id="plan-agent.system",
        role="system",
        content=_build_plan_prompt(output_dir_abs, project_path_abs),
        supported_models=[],
        order=0,
    )

    # plan-agent 使用与 sub-agents 相同的 workspace 规则
    plan_config = replace(base_config, mcp_paths=[])
    plan_agent = await (
        BaseAgent.react_agent_builder("plan-agent")
        .with_config(plan_config)
        .with_model(model)
        .with_context_strategy("basic")
        .with_prompt(plan_prompt)
        .with_plan_provider(planner)
        .add_tools(ReadFileTool())
        .with_skill_tool(False)
        .with_max_tool_rounds(30)
        .build()
    )

    print("对标 Claude Code - 项目级 AI 编程助手（意图驱动）")
    print("  Sub-agents: sub_agent_recon (只读) | sub_agent_coder (可写) | sub_agent_runner (可执行)")
    print(f"  Model: {model_name}")
    print(f"  目标工程: {project_path_abs}")
    print(f"  产物路径: {output_dir_abs}")
    _print_help(project_path_abs)
    print("-" * 60)

    while True:
        try:
            raw = input("\ntask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.", flush=True)
            return

        if not raw:
            continue

        # 优先处理 /resume 命令：基于 checkpoint 恢复 agent_state（当前仅 STM）
        if raw.startswith("/resume"):
            parts = raw.split(maxsplit=1)
            checkpoint_id: str | None = None

            # /resume（无参数）：先列出可选 checkpoint，再由用户选择
            if len(parts) < 2 or not parts[1].strip():
                checkpoints = checkpointer.list(print_to_stdout=True)
                if not checkpoints:
                    continue
                choice = input("请输入要恢复的 checkpoint 序号或 ID（回车取消）: ").strip()
                if not choice:
                    continue

                # 支持按序号选择
                if choice.isdigit():
                    index = int(choice)
                    if 1 <= index <= len(checkpoints):
                        checkpoint_id = checkpoints[index - 1].checkpoint_id
                # 或者按 ID / 前缀选择
                if checkpoint_id is None:
                    for cp in checkpoints:
                        if cp.checkpoint_id.startswith(choice):
                            checkpoint_id = cp.checkpoint_id
                            break
                if checkpoint_id is None:
                    print("未找到匹配的 checkpoint。", flush=True)
                    continue

            # /resume <checkpoint_id>：直接按提供的 ID 恢复
            if checkpoint_id is None:
                checkpoint_id = parts[1].strip()

            try:
                checkpointer.restore(checkpoint_id, plan_agent.context)
            except KeyError:
                print(f"Checkpoint 不存在: {checkpoint_id}", flush=True)
            except Exception as exc:
                print(f"恢复 checkpoint 失败: {exc}", flush=True)
            else:
                print(f"已从 checkpoint {checkpoint_id} 恢复 agent_state（当前仅 STM）。", flush=True)
            continue

        parsed = _parse_command(raw)
        if isinstance(parsed, CommandType):
            if parsed is CommandType.QUIT:
                print("Bye.", flush=True)
                return
            if parsed is CommandType.HELP:
                _print_help(project_path_abs)
                continue
            continue
        task_text = parsed[1] if isinstance(parsed, tuple) else raw

        # 每轮新任务前重置 plan 状态
        _reset_plan_state(state)

        result = await plan_agent(task_text)
        output_text = result.output_text or str(result.output)
        print(f"\nAssistant: {output_text}", flush=True)
        if result.errors:
            print(f"Errors: {result.errors}", flush=True)

        # 每轮任务结束后自动保存一次 agent_state checkpoint（当前仅 STM），便于后续 /resume 回到本轮结束现场
        try:
            checkpoint_id = checkpointer.save(plan_agent.context)
            print(f"[checkpoint] 本轮任务结束后已保存 agent_state checkpoint: {checkpoint_id}", flush=True)
        except Exception as exc:
            print(f"[checkpoint] 自动保存 checkpoint 失败: {exc}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
