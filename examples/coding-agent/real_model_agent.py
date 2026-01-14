"""
Real Model Coding Agent Example

Run:
  PYTHONPATH=../.. python real_model_agent.py

Requires:
  export OPENAI_API_KEY="your_api_key"
  optional: export OPENAI_MODEL="gpt-4o-mini"
  optional: export OPENAI_BASE_URL="https://api.openai.com/v1"
  optional: export OPENAI_DEBUG=1
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from agent import CodingAgent
from openai_adapter import OpenAIModelAdapter, OpenAIPlanGenerator, tool_definitions_from_tools
from plan_helpers import DEFAULT_EDIT_TEXT
from tools import EditLineTool, ReadFileTool, RunTestsTool, SearchCodeTool, WriteFileTool


async def main() -> None:
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
    temp_line = DEFAULT_EDIT_TEXT

    tools = [
        EditLineTool(workspace="."),
        ReadFileTool(workspace="."),
        WriteFileTool(workspace="."),
        SearchCodeTool(workspace="."),
        RunTestsTool(),
    ]

    adapter = OpenAIModelAdapter(model=model_name, base_url=base_url)
    plan_generator = OpenAIPlanGenerator(
        model=adapter,
        tool_definitions=tool_definitions_from_tools(tools),
        plan_tools=["fix_bug"],
    )

    agent = CodingAgent(
        workspace=".",
        mock_mode=False,
        model_adapter=adapter,
        plan_generator=plan_generator,
        event_log_path=".dare/examples/coding-agent/real/event_log.jsonl",
        checkpoint_path=".dare/examples/coding-agent/real/checkpoints",
    )

    result = await agent.run(
        (
            "Read README.md, insert the exact line "
            f'"{temp_line}" at line 2, then read the file to confirm it, '
            "then delete that exact line."
        )
    )
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    _verify_chain(result.output or [], temp_line)


def _verify_chain(outputs, temp_line: str) -> None:
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
        final_content = Path("README.md").read_text(encoding="utf-8")
        if temp_line in final_content:
            print("[verify] temp line still present after run")
        else:
            print("[verify] temp line removed from file")
    except OSError as exc:
        print(f"[verify] unable to read README.md for final check: {exc}")


def _is_mode(output, mode: str) -> bool:
    if not output or not hasattr(output, "output"):
        return False
    return output.output.get("mode") == mode


if __name__ == "__main__":
    asyncio.run(main())
