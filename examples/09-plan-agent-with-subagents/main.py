"""Example 09: Plan Agent + sub-agents（两类 sub-agent）.

Skill 源：config.skill_paths（本示例为 D:\\Agent\\skills\\skills），不手写 skill。

- Plan Agent：仅 plan tools（无 search_skill、MCP、native tools）。
- sub_agent_general：native + MCP + auto skill，可 search_skill 到该路径下每一种 skill。
- sub_agent_special_{id}：为 config.skill_paths 下的每一种 skill 各创建一个 sub-agent，该 skill 常驻其 system prompt；native + MCP。
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.agent import BaseAgent
from dare_framework.config import FileConfigProvider
from dare_framework.model import OpenRouterModelAdapter
from dare_framework.model.types import Prompt
from dare_framework.plan_v2 import (
    PLAN_AGENT_SYSTEM_PROMPT,
    SUB_AGENT_TASK_PROMPT,
    Planner,
    PlannerState,
    SubAgentRegistry,
)
from dare_framework.skill._internal.filesystem_skill_loader import FileSystemSkillLoader
from dare_framework.skill._internal.prompt_enricher import enrich_prompt_with_skill
from dare_framework.skill.types import Skill
from dare_framework.tool._internal.tools import (
    EchoTool,
    NoopTool,
    ReadFileTool,
    RunCommandTool,
    SearchCodeTool,
    WriteFileTool,
    EditLineTool,
)

EXAMPLE_DIR = Path(__file__).resolve().parent

NATIVE_TOOLS = [
    EchoTool(),
    NoopTool(),
    ReadFileTool(),
    WriteFileTool(),
    EditLineTool(),
    RunCommandTool(),
    SearchCodeTool(),
]


def _load_all_skills_from_config_paths(workspace_dir: Path, skill_paths: list[str]) -> list[Skill]:
    workspace_root = workspace_dir.resolve()
    resolved: list[Path] = []
    for p in skill_paths:
        path = Path(p).expanduser()
        if not path.is_absolute():
            path = (workspace_root / path).resolve()
        resolved.append(path)
    if not resolved:
        return []
    loader = FileSystemSkillLoader(*resolved)
    return loader.load()


async def main() -> None:
    api_key = os.getenv("OPENROUTER_API_KEY", "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")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        sys.exit(1)

    model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")
    max_tokens = min(int(os.getenv("OPENROUTER_MAX_TOKENS", "4096")), 8192)

    _explore_dir = "agentscope/examples/agent/a2a_agent"
    DEFAULT_TASK = (
        f"制定计划并执行，对本仓库中的 {_explore_dir} 目录做一次代码侦察，产出一份简短报告。"
        f"第一步：委托 sub_agent_general，让他在 {_explore_dir} 下搜索包含 'Agent' 或 'a2a' 的代码，列出命中的文件路径及每文件出现次数。"
        f"第二步：委托 sub_agent_general，让他读取 {_explore_dir}/README.md 和 {_explore_dir}/main.py，提炼该示例的用途和入口逻辑。"
        f"第三步：委托 sub_agent_general，让他把前两步的结果整理成一份报告，写入 workspace/a2a_agent_recon.md。报告须包含："
        "(1) 命中文件列表；(2) README 与 main 的摘要；(3) 用一两句话说明该 a2a_agent 示例的作用。"
        "执行完三步后，汇总并报告是否已生成 workspace/a2a_agent_recon.md 以及其要点。"
    )
    task_description = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK

    _file_provider = FileConfigProvider(workspace_dir=EXAMPLE_DIR, user_dir=Path.home())

    class _ProjectRootConfigProvider:
        def current(self):
            return replace(_file_provider.current(), workspace_dir=str(PROJECT_ROOT))

        def reload(self):
            return replace(_file_provider.reload(), workspace_dir=str(PROJECT_ROOT))

    config_provider = _ProjectRootConfigProvider()
    config = config_provider.current()
    skill_paths = getattr(config, "skill_paths", None) or []
    all_skills = _load_all_skills_from_config_paths(EXAMPLE_DIR, skill_paths)

    (EXAMPLE_DIR / "workspace").mkdir(exist_ok=True)
    (PROJECT_ROOT / "workspace").mkdir(exist_ok=True)

    await _run_agents(
        api_key=api_key,
        model_name=model_name,
        max_tokens=max_tokens,
        task_description=task_description,
        config_provider=config_provider,
        skill_paths=skill_paths,
        all_skills=all_skills,
    )


async def _run_agents(
    *,
    api_key: str,
    model_name: str,
    max_tokens: int,
    task_description: str,
    config_provider,
    skill_paths: list[str],
    all_skills: list[Skill],
) -> None:
    model = OpenRouterModelAdapter(
        model=model_name,
        api_key=api_key,
        extra={"max_tokens": max_tokens},
    )

    sub_prompt = Prompt(
        prompt_id="sub-agent.system",
        role="system",
        content=SUB_AGENT_TASK_PROMPT,
        supported_models=[],
        order=0,
    )

    general_builder = (
        BaseAgent.react_agent_builder("sub_agent_general")
        .with_model(model)
        .with_config_provider(config_provider)
        .with_prompt(sub_prompt)
        .with_skill_tool(True)
    )
    for t in NATIVE_TOOLS:
        general_builder = general_builder.add_tools(t)
    general_agent = await general_builder.build()

    registry = SubAgentRegistry()
    registry.register(
        "sub_agent_general",
        "通用 sub-agent：native tools、MCP、auto skill（search_skill 可搜索 config.skill_paths 下每一种 skill）。适合通用步骤。",
        lambda: general_agent,
    )

    for skill in all_skills:
        enriched_prompt = enrich_prompt_with_skill(sub_prompt, skill)
        agent_id = f"sub_agent_special_{skill.id}"
        builder = (
            BaseAgent.react_agent_builder(agent_id)
            .with_model(model)
            .with_config_provider(config_provider)
            .with_prompt(enriched_prompt)
            .with_skill_tool(False)
        )
        for t in NATIVE_TOOLS:
            builder = builder.add_tools(t)
        agent = await builder.build()
        cap_desc = f"专用 sub-agent（持久化 skill「{skill.name}」）：{skill.description or skill.id}"
        registry.register(agent_id, cap_desc, lambda a=agent: a)

    state = PlannerState(task_id="example-09-task-1", session_id="example-09-session-1")
    planner = Planner(state, sub_agent_registry=registry)

    plan_prompt = Prompt(
        prompt_id="plan-agent.system",
        role="system",
        content=PLAN_AGENT_SYSTEM_PROMPT,
        supported_models=[],
        order=0,
    )

    plan_config = replace(config_provider.current(), mcp_paths=[])
    plan_builder = (
        BaseAgent.react_agent_builder("plan-agent")
        .with_config(plan_config)
        .with_model(model)
        .with_prompt(plan_prompt)
        .with_plan_provider(planner)
        .with_skill_tool(False)
        .with_max_tool_rounds(25)
    )
    # Plan agent 仅 plan tools（来自 planner），无 search_skill、MCP、native tools
    plan_agent = await plan_builder.build()

    print("Plan Agent + sub-agents (plan_v2)")
    print("  Skill 源: config.skill_paths =", skill_paths)
    print("  Plan Agent: 仅 plan tools（无 search_skill、MCP、native tools）")
    print("  Sub-agents: sub_agent_general (auto skill) + sub_agent_special_* (持久化 skill)")
    print(f"  Model: {model_name}")
    print(f"  Task: {task_description}")
    print("-" * 60)
    print("Plan Agent 开始执行...（首次 LLM 调用及 sub-agent 执行可能需要较长时间）")
    print("-" * 60)

    result = await plan_agent.run(task_description)
    content = (result.output or result.output_text or "") if hasattr(result, "output") else str(result)
    print("Plan Agent final output:")
    print(content)
    print("-" * 60)

    pp = getattr(plan_agent, "plan_provider", None)
    if pp is not None:
        plan_state = getattr(pp, "state", None)
        if plan_state is not None:
            print("PlannerState:")
            print(f"  plan_description: {plan_state.plan_description or '(empty)'}")
            print(f"  steps: {len(plan_state.steps)}")
            for i, s in enumerate(plan_state.steps):
                print(f"    [{i+1}] {s.step_id}: {s.description}")


if __name__ == "__main__":
    asyncio.run(main())
