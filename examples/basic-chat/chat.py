from __future__ import annotations

import asyncio
import os

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

MODEL = "z-ai/glm-4.5-air:free"
API_KEY = os.getenv("api_sk")
ENDPOINT = "https://openrouter.ai/api/v1"


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

        result = await agent.run(Task(description=prompt), None)
        content = ""
        if result.output:
            last = result.output[-1]
            content = getattr(last, "output", {}).get("content", "")
        if not content:
            print("No output returned.", flush=True)
            continue

        print(content, flush=True)
        history.append(Message(role="user", content=prompt))
        history.append(Message(role="assistant", content=content))


if __name__ == "__main__":
    asyncio.run(main())
