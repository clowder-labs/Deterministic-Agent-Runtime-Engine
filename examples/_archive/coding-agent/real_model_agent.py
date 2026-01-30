"""
Real Model Coding Agent Example

Run:
  python real_model_agent.py

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
import sys
from pathlib import Path

# This example intentionally targets the archived framework implementation under
# `archive/frameworks/dare_framework/` and is not expected to run against the
# canonical `dare_framework` package at repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_FRAMEWORKS = PROJECT_ROOT / "archive" / "frameworks"
if str(ARCHIVE_FRAMEWORKS) not in sys.path:
    sys.path.insert(0, str(ARCHIVE_FRAMEWORKS))

from dare_framework.builder import AgentBuilder
from dare_framework.execution.impl.event.local_event_log import LocalEventLog

from openai_adapter import OpenAIModelAdapter, OpenAIPlanner, tool_definitions_from_tools
from plan_helpers import DEFAULT_EDIT_TEXT
from tools import EditLineTool, ReadFileTool, RunTestsTool, SearchCodeTool, WriteFileTool


async def main() -> None:
    model_name = os.getenv("OPENAI_MODEL", "z-ai/glm-4.5-air:free")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
    temp_line = DEFAULT_EDIT_TEXT
    workspace = str(PROJECT_ROOT)
    target_path = "examples/coding-agent/verify_sample.txt"

    tools = [
        EditLineTool(workspace=workspace),
        ReadFileTool(workspace=workspace),
        WriteFileTool(workspace=workspace),
        SearchCodeTool(workspace=workspace),
        RunTestsTool(),
    ]

    adapter = OpenAIModelAdapter(model=model_name, base_url=base_url)
    planner = OpenAIPlanner(
        model=adapter,
        tool_definitions=tool_definitions_from_tools(tools),
        plan_tools=["fix_bug"],
        default_read_path=target_path,
    )

    agent = (
        AgentBuilder("coding-agent-real")
        .with_kernel_defaults()
        .with_tools(*tools)
        .with_planner(planner)
        .with_event_log(LocalEventLog(path=".dare/examples/coding-agent/real/event_log.jsonl"))
        .with_checkpoint_dir(".dare/examples/coding-agent/real/checkpoints")
        .build()
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
    _verify_chain(result.output or [], temp_line, PROJECT_ROOT / target_path)


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
