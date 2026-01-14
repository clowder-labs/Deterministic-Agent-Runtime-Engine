from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.components.context_assembler import BasicContextAssembler
from dare_framework.components.hooks.stdout import StdoutHook
from dare_framework.components.model_adapters.openai import OpenAIModelAdapter
from dare_framework.components.prompt_stores.in_memory import InMemoryPromptStore
from dare_framework.components.tools.run_command import RunCommandTool
from dare_framework.composition.builder import AgentBuilder
from dare_framework.core.context import IContextAssembler
from dare_framework.core.models.context import AssembledContext, Message, MilestoneContext
from dare_framework.core.models.plan import Milestone, Task
from dare_framework.core.models.runtime import RunContext

MODEL = "qwen-7b"
API_KEY = os.getenv("api_sk")
ENDPOINT = "http://localhost:8000/v1"
LOG_LEVEL = os.getenv("CHAT_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("basic-chat")


def _preview(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated>"


class HistoryContextAssembler(BasicContextAssembler, IContextAssembler):
    def __init__(self, prompt_store: InMemoryPromptStore, history: list[Message]) -> None:
        super().__init__(prompt_store)
        self._history = history

    async def assemble(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> AssembledContext:
        messages = [Message(role="system", content=self._get_base_prompt())]
        messages.extend(self._history)
        messages.append(Message(role="user", content=milestone_ctx.user_input))
        return AssembledContext(messages=messages)


async def main() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info(
        "boot basic chat agent",
        extra={"model": MODEL, "endpoint": ENDPOINT, "api_key_set": bool(API_KEY)},
    )
    history: list[Message] = []
    prompt_store = InMemoryPromptStore()
    context_assembler = HistoryContextAssembler(prompt_store, history)

    builder = AgentBuilder("basic-chat")
    builder.with_prompt_store(prompt_store)
    builder.with_context_assembler(context_assembler)
    builder.with_model(OpenAIModelAdapter(model=MODEL, api_key=API_KEY, endpoint=ENDPOINT))
    builder.with_tools(RunCommandTool())
    builder.with_hook(StdoutHook())
    agent = builder.build()

    while True:
        try:
            raw = input()
        except EOFError:
            break
        prompt = raw.strip()
        if not prompt:
            continue
        if prompt == "/quit":
            break

        logger.info(
            "running prompt",
            extra={"prompt": _preview(prompt), "history_entries": len(history)},
        )
        try:
            result = await agent.run(Task(description=prompt), None)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "agent run failed",
                extra={"model": MODEL, "endpoint": ENDPOINT},
            )
            print(f"[error] model call failed: {exc}", file=sys.stderr, flush=True)
            continue

        content = ""
        if result.output:
            last = result.output[-1]
            content = getattr(last, "output", {}).get("content", "")
        if not content:
            logger.warning("no content returned from agent")
            print("No output returned.", flush=True)
            continue

        logger.info(
            "assistant reply",
            extra={"content": _preview(content), "history_entries": len(history)},
        )
        print(content, flush=True)
        history.append(Message(role="user", content=prompt))
        history.append(Message(role="assistant", content=content))


if __name__ == "__main__":
    asyncio.run(main())
