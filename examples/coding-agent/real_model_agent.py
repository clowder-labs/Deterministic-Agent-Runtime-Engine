"""
Real Model Coding Agent Example

Run:
  PYTHONPATH=../.. python real_model_agent.py

Requires:
  export OPENAI_API_KEY="your_api_key"
  optional: export OPENAI_MODEL="gpt-4o-mini"
  optional: export OPENAI_BASE_URL="https://api.openai.com/v1"
  optional: export OPENROUTER_API_KEY="your_openrouter_key"
  optional: export OPENROUTER_HTTP_REFERER="https://your.app"
  optional: export OPENROUTER_APP_TITLE="dare-example"
  optional: export OPENAI_DEBUG=1
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Iterable

from dare_framework.core.context import IContextAssembler
from dare_framework.core.models.context import AssembledContext, Message, MilestoneContext
from dare_framework.core.models.plan import Milestone
from dare_framework.core.models.runtime import RunContext

from agent import CodingAgent
from openai_adapter import OpenAIModelAdapter, OpenAIPlanGenerator, tool_definitions_from_tools
from plan_helpers import DEFAULT_EDIT_TEXT
from tools import EditLineTool, ReadFileTool, RunTestsTool, SearchCodeTool, WriteFileTool


class StrictToolContextAssembler(IContextAssembler):
    """Context assembler that nudges the model to only call the allowed tools."""

    def __init__(self, tool_names: Iterable[str]) -> None:
        self._tool_names = sorted(tool_names)

    async def assemble(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> AssembledContext:
        tool_list = ", ".join(self._tool_names)
        system_prompt = (
            "You are a tool-using agent. "
            "You MUST call one of the allowed tools to make progress. "
            f"Allowed tools: {tool_list}. "
            "Do not invent tool names. "
            "Only respond with a final answer after tools are complete."
        )
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=milestone_ctx.user_input),
        ]
        return AssembledContext(messages=messages)

    async def compress(self, context: AssembledContext, max_tokens: int) -> AssembledContext:
        return context


async def main() -> None:
    model_name = os.getenv("OPENAI_MODEL", "z-ai/glm-4.5-air:free")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
    temp_line = DEFAULT_EDIT_TEXT
    repo_root = Path(__file__).resolve().parents[2]
    workspace = str(repo_root)
    target_path = "examples/coding-agent/verify_sample.txt"

    tools = [
        EditLineTool(workspace=workspace),
        ReadFileTool(workspace=workspace),
        WriteFileTool(workspace=workspace),
        SearchCodeTool(workspace=workspace),
        RunTestsTool(),
    ]

    tool_names = [tool.name for tool in tools]
    adapter = OpenAIModelAdapter(model=model_name, base_url=base_url)
    plan_generator = OpenAIPlanGenerator(
        model=adapter,
        tool_definitions=tool_definitions_from_tools(tools),
        plan_tools=["fix_bug"],
        default_read_path=target_path,
    )

    agent = CodingAgent(
        workspace=workspace,
        mock_mode=False,
        model_adapter=adapter,
        plan_generator=plan_generator,
        context_assembler=StrictToolContextAssembler(tool_names),
        event_log_path=".dare/examples/coding-agent/real/event_log.jsonl",
        checkpoint_path=".dare/examples/coding-agent/real/checkpoints",
        enable_skills=False,
    )

    result = await agent.run(
        (
            "Use the available tools to complete this task. "
            f"Read {target_path}, insert the exact line "
            f'"{temp_line}" at line 2, then read the file to confirm it, '
            "then delete that exact line. "
            "Do not reply with manual instructions."
        )
    )
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    _verify_chain(result.output or [], temp_line, repo_root / target_path)


def _verify_chain(outputs, temp_line: str, target_path: Path) -> None:
    saw_insert = False
    saw_delete = False
    saw_confirm = False

    for output in outputs:
        evidence = getattr(output, "evidence", [])
        for item in evidence:
            if getattr(item, "kind", "") == "file_edit":
                saw_insert = saw_insert or _is_mode(output, "insert")
                saw_delete = saw_delete or _is_mode(output, "delete")
            if getattr(item, "kind", "") == "file_read":
                content = output.output.get("content", "") if output.output else ""
                if temp_line in content:
                    saw_confirm = True

    if not saw_insert:
        print("[verify] missing insert evidence")
    if not saw_confirm:
        print("[verify] missing confirmation read (line not found)")
    if not saw_delete:
        print("[verify] missing delete evidence")

    if saw_insert and saw_confirm and saw_delete:
        print("[verify] plan chain completed: insert -> confirm -> delete")

    try:
        final_content = target_path.read_text(encoding="utf-8")
        if temp_line in final_content:
            print("[verify] temp line still present after run")
        else:
            print("[verify] temp line removed from file")
    except OSError as exc:
        print(f"[verify] unable to read {target_path} for final check: {exc}")


def _is_mode(output, mode: str) -> bool:
    if not output or not hasattr(output, "output"):
        return False
    return output.output.get("mode") == mode


if __name__ == "__main__":
    asyncio.run(main())
