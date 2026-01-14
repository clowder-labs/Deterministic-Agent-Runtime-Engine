"""
Simple Coding Agent Example

这个文件展示如何使用 DARE Framework 构建一个 Coding Agent。
通过这个示例验证框架的接口设计是否合理。
"""

from typing import Any, Iterable

from dare_framework.components.checkpoint import FileCheckpoint
from dare_framework.components.event_log import LocalEventLog
from dare_framework.components.plan_generator import DeterministicPlanGenerator
from dare_framework.composition.builder import AgentBuilder
from dare_framework.core.context import IContextAssembler, IModelAdapter
from dare_framework.core.models.context import MilestoneContext
from dare_framework.core.models.plan import Milestone, ProposedPlan, ProposedStep, Task
from dare_framework.core.models.runtime import RunContext, new_id
from dare_framework.core.planning import IPlanGenerator

from plan_helpers import FIX_HINTS, build_demo_steps, contains_any, read_envelope, seen_plan_tool
from skills.fix_bug import FixBugSkill
from tools.edit_line import EditLineTool
from tools.read_file import ReadFileTool
from tools.run_tests import RunTestsTool
from tools.search_code import SearchCodeTool
from tools.write_file import WriteFileTool


class DemoPlanGenerator(IPlanGenerator):
    """Generate a small, deterministic plan that exercises the current loop design."""

    def __init__(self, default_read_path: str = "README.md") -> None:
        self._default_read_path = default_read_path

    async def generate_plan(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        plan_attempts: list[dict[str, Any]],
        ctx: RunContext,
    ) -> ProposedPlan:
        raw_description = milestone.description
        description = raw_description.lower()

        # Use a plan tool once to demonstrate the plan tool -> replan signal path.
        if contains_any(description, FIX_HINTS) and not seen_plan_tool(milestone_ctx, "fix_bug"):
            steps = [
                ProposedStep(
                    step_id=new_id("step"),
                    tool_name="fix_bug",
                    tool_input={"goal": raw_description},
                )
            ]
            return ProposedPlan(
                plan_description="request plan tool for bug fixing",
                proposed_steps=steps,
                attempt=len(plan_attempts),
            )

        steps = build_demo_steps(description, raw_description, self._default_read_path)
        if not steps:
            steps = [
                ProposedStep(
                    step_id=new_id("step"),
                    tool_name="read_file",
                    tool_input={"path": self._default_read_path},
                    envelope=read_envelope(),
                )
            ]

        return ProposedPlan(
            plan_description=milestone.description,
            proposed_steps=steps,
            attempt=len(plan_attempts),
        )


class CodingAgent:
    """
    Coding Agent 示例

    能力：
    - 读写代码文件
    - 搜索代码
    - 运行测试
    - 修复 Bug
    """

    def __init__(
        self,
        workspace: str = ".",
        mock_mode: bool = True,
        plan_steps: Iterable[ProposedStep] | None = None,
        model_adapter: IModelAdapter | None = None,
        plan_generator: IPlanGenerator | None = None,
        context_assembler: IContextAssembler | None = None,
        event_log_path: str | None = None,
        checkpoint_path: str | None = None,
        demo_plan: bool = True,
        enable_skills: bool = True,
    ) -> None:
        builder = (
            AgentBuilder("coding-agent")
            .with_tools(
                EditLineTool(workspace=workspace),
                ReadFileTool(workspace=workspace),
                WriteFileTool(workspace=workspace),
                SearchCodeTool(workspace=workspace),
                RunTestsTool(),
            )
        )
        if enable_skills:
            builder.with_skills(FixBugSkill())
        if context_assembler is not None:
            builder.with_context_assembler(context_assembler)

        if mock_mode:
            steps = list(plan_steps) if plan_steps else []
            if plan_generator is not None:
                builder.with_plan_generator(plan_generator)
            elif steps:
                builder.with_plan_generator(DeterministicPlanGenerator([steps]))
            elif demo_plan:
                builder.with_plan_generator(DemoPlanGenerator())
            else:
                fallback = [
                    ProposedStep(
                        step_id=new_id("step"),
                        tool_name="read_file",
                        tool_input={"path": "README.md"},
                    )
                ]
                builder.with_plan_generator(DeterministicPlanGenerator([fallback]))
        else:
            if model_adapter is None or plan_generator is None:
                raise ValueError(
                    "model_adapter and plan_generator are required when mock_mode=False"
                )
            builder.with_model(model_adapter)
            builder.with_plan_generator(plan_generator)

        if event_log_path:
            builder.with_event_log(LocalEventLog(path=event_log_path))
        if checkpoint_path:
            builder.with_checkpoint(FileCheckpoint(path=checkpoint_path))

        self._agent = builder.build()

    async def run(self, task: str | Task, deps: Any | None = None):
        task_obj = task if isinstance(task, Task) else Task(description=task)
        return await self._agent.run(task_obj, deps)


async def main() -> None:
    agent = CodingAgent(
        workspace=".",
        mock_mode=True,
        event_log_path=".dare/examples/coding-agent/event_log.jsonl",
        checkpoint_path=".dare/examples/coding-agent/checkpoints",
    )

    result = await agent.run(task="读取 README.md 并解释内容")
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
