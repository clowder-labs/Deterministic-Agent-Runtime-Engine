"""Task execution and plan-preview helpers."""

from __future__ import annotations

from typing import Any

from dare_framework.config import Config
from dare_framework.context import Context, Message
from dare_framework.plan import DefaultPlanner


def format_run_output(output: Any) -> str | None:
    """Normalize RunResult.output into printable text."""
    if output is None:
        return None
    if isinstance(output, str):
        text = output.strip()
        return text or None
    if isinstance(output, dict) and "content" in output:
        content = output["content"]
        if content is None:
            return None
        text = content.strip() if isinstance(content, str) else str(content).strip()
        return text or None
    text = str(output).strip()
    return text or None


async def preview_plan(
    *,
    task_text: str,
    model: Any,
    workspace_dir: str,
    user_dir: str,
) -> Any:
    """Run planner-only preview for ``/mode plan``."""
    ctx = Context(
        id="cli-plan-preview",
        config=Config(workspace_dir=workspace_dir, user_dir=user_dir),
    )
    ctx.stm_add(Message(role="user", text=task_text))
    planner = DefaultPlanner(model, verbose=False)
    return await planner.plan(ctx)


async def run_task(
    *,
    agent: Any,
    task_text: str,
    conversation_id: str | None = None,
    transport: Any | None = None,
) -> Any:
    """Execute one task using direct agent call for metadata support."""
    metadata: dict[str, Any] = {}
    if isinstance(conversation_id, str) and conversation_id.strip():
        metadata["conversation_id"] = conversation_id.strip()
    task = Message(role="user", text=task_text, metadata=metadata)
    if transport is None:
        return await agent(task)
    return await agent(task, transport=transport)
