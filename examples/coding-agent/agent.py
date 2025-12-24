"""
Simple Coding Agent Example

这个文件展示如何使用 DARE Framework 构建一个 Coding Agent。
通过这个示例验证框架的接口设计是否合理。
"""

from typing import Iterable

from dare_framework import AgentBuilder
from dare_framework.defaults import DeterministicPlanGenerator, MockModelAdapter
from dare_framework.models import PlanStep, Task, new_id

from tools import ReadFileTool, WriteFileTool, SearchCodeTool, RunTestsTool
from skills import FixBugSkill


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
        plan_steps: Iterable[PlanStep] | None = None,
        model_adapter=None,
        plan_generator=None,
    ) -> None:
        builder = AgentBuilder("coding-agent").with_tools(
            ReadFileTool(workspace=workspace),
            WriteFileTool(workspace=workspace),
            SearchCodeTool(workspace=workspace),
            RunTestsTool(),
        ).with_skills(FixBugSkill())

        if mock_mode:
            steps = list(plan_steps) if plan_steps else [
                PlanStep(step_id=new_id("step"), tool_name="read_file", tool_input={"path": "README.md"})
            ]
            builder.with_plan_generator(DeterministicPlanGenerator([steps]))
            builder.with_model(MockModelAdapter(["mock"]))
        else:
            if model_adapter is None or plan_generator is None:
                raise ValueError("model_adapter and plan_generator are required when mock_mode=False")
            builder.with_model(model_adapter)
            builder.with_plan_generator(plan_generator)

        self._agent = builder.build()

    async def run(self, task: str):
        return await self._agent.run(Task(description=task), None)


async def main() -> None:
    agent = CodingAgent(
        workspace=".",
        mock_mode=True,
    )

    result = await agent.run(task="读取 README.md 并解释内容")
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
