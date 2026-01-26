"""
Simple Coding Agent Example (legacy kernel dependencies)

这个文件展示如何使用已归档的 Kernel 架构构建一个 Coding Agent。
示例重点：用最少依赖跑通 Plan → Execute → Tool → Verify 的闭环接口。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# This example intentionally targets the archived framework implementation under
# `archive/frameworks/dare_framework/` and is not expected to run against the
# canonical `dare_framework` package at repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_FRAMEWORKS = PROJECT_ROOT / "archive" / "frameworks"
if str(ARCHIVE_FRAMEWORKS) not in sys.path:
    sys.path.insert(0, str(ARCHIVE_FRAMEWORKS))

from dare_framework.builder import AgentBuilder
from dare_framework.plan.impl.planners.deterministic import DeterministicPlanner
from dare_framework.contracts.ids import generator_id
from dare_framework.execution.impl.event.local_event_log import LocalEventLog
from dare_framework.plan.planning import ProposedStep
from dare_framework.plan.task import Task

from tools.edit_line import EditLineTool
from tools.read_file import ReadFileTool
from tools.run_tests import RunTestsTool
from tools.search_code import SearchCodeTool
from tools.write_file import WriteFileTool


class CodingAgent:
    """A minimal coding-agent composition using archived kernel dependencies."""

    def __init__(
        self,
        *,
        workspace: str = ".",
        plan_steps: list[ProposedStep] | None = None,
        event_log_path: str | None = None,
        checkpoint_dir: str | None = None,
    ) -> None:
        tools = [
            EditLineTool(workspace=workspace),
            ReadFileTool(workspace=workspace),
            WriteFileTool(workspace=workspace),
            SearchCodeTool(workspace=workspace),
            RunTestsTool(),
        ]

        steps = plan_steps or [_tool_step("read_file", {"path": "README.md"})]
        planner = DeterministicPlanner([steps])

        builder = AgentBuilder("coding-agent").with_kernel_defaults().with_tools(*tools).with_planner(planner)
        if event_log_path is not None:
            builder.with_event_log(LocalEventLog(path=event_log_path))
        if checkpoint_dir is not None:
            builder.with_checkpoint_dir(checkpoint_dir)

        self._agent = builder.build()

    async def run(self, task: str | Task, deps: Any | None = None):
        return await self._agent.run(task, deps=deps)


def _tool_step(tool_name: str, params: dict[str, Any]) -> ProposedStep:
    """Build a canonical tool capability step (capability_id = 'tool:<name>')."""

    return ProposedStep(step_id=generator_id("step"), capability_id=f"tool:{tool_name}", params=params)


async def main() -> None:
    agent = CodingAgent(
        workspace=".",
        event_log_path=".dare/examples/coding-agent/event_log.jsonl",
        checkpoint_dir=".dare/examples/coding-agent/checkpoints",
    )

    result = await agent.run(task="读取 README.md 并解释内容")
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
