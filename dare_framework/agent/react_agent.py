"""ReactAgent - Chat agent with ReAct tool loop (Reason → Act → Observe).

When the model returns tool_calls, this agent executes them, adds tool results
to context, and calls the model again until the model returns a final text response.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dare_framework.agent.base_agent import BaseAgent
from dare_framework.context import Context, Message
from dare_framework.model import IModelAdapter, ModelInput
from dare_framework.plan.types import Envelope
from dare_framework.tool import IToolProvider

if TYPE_CHECKING:
    from dare_framework.context import Budget
    from dare_framework.memory import IShortTermMemory, ILongTermMemory
    from dare_framework.knowledge import IKnowledge
    from dare_framework.transport.kernel import AgentChannel


class ReactAgent(BaseAgent):
    """Chat agent that executes tool calls in a ReAct loop.

    Same context-centric setup as SimpleChatAgent, but when the model returns
    tool_calls, executes each tool via the context's tool provider (e.g. ToolManager),
    adds tool result messages to STM, reassembles, and calls the model again.
    Loops until the model returns no tool_calls, then returns that content.
    """

    def __init__(
        self,
        name: str,
        *,
        model: IModelAdapter,
        context: Context | None = None,
        short_term_memory: IShortTermMemory | None = None,
        long_term_memory: ILongTermMemory | None = None,
        knowledge: IKnowledge | None = None,
        tools: IToolProvider | None = None,
        budget: Budget | None = None,
        max_tool_rounds: int = 10,
        agent_channel: AgentChannel | None = None,
    ) -> None:
        super().__init__(name, agent_channel=agent_channel)
        self._model = model
        self._max_tool_rounds = max_tool_rounds

        if context is None:
            from dare_framework.context import Budget
            self._context = Context(
                id=f"context_{name}",
                short_term_memory=short_term_memory,
                long_term_memory=long_term_memory,
                knowledge=knowledge,
                budget=budget or Budget(),
            )
            if tools is not None:
                self._context._tool_gateway = tools
        else:
            self._context = context

    @property
    def context(self) -> Context:
        return self._context

    async def _execute(self, task: str) -> str:
        user_message = Message(role="user", content=task)
        self._context.stm_add(user_message)

        gateway = getattr(self._context, "_tool_gateway", None)
        has_invoke = gateway is not None and hasattr(gateway, "invoke")

        for _ in range(self._max_tool_rounds):
            assembled = self._context.assemble()
            messages = list(assembled.messages)
            prompt_def = getattr(assembled, "sys_prompt", None)
            if prompt_def is not None:
                messages = [
                    Message(
                        role=prompt_def.role,
                        content=prompt_def.content,
                        name=prompt_def.name,
                        metadata=dict(prompt_def.metadata),
                    ),
                    *messages,
                ]

            model_input = ModelInput(
                messages=messages,
                tools=assembled.tools,
                metadata=assembled.metadata,
            )
            response = await self._model.generate(model_input)

            if response.usage:
                tokens = response.usage.get("total_tokens", 0)
                if tokens:
                    self._context.budget_use("tokens", tokens)
            self._context.budget_check()

            if not response.tool_calls:
                assistant_message = Message(role="assistant", content=response.content or "")
                self._context.stm_add(assistant_message)
                return response.content or ""

            if not has_invoke:
                assistant_message = Message(
                    role="assistant",
                    content=response.content or "(Tool calls returned but no tool gateway to execute them.)",
                )
                self._context.stm_add(assistant_message)
                return response.content or "(Tool calls not executed.)"

            assistant_msg = Message(
                role="assistant",
                content=response.content or "",
                metadata={"tool_calls": response.tool_calls},
            )
            self._context.stm_add(assistant_msg)

            envelope = Envelope()
            for tool_call in response.tool_calls:
                name = tool_call.get("name", "")
                tool_call_id = tool_call.get("id", "")
                args = tool_call.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args) if args.strip() else {}
                    except json.JSONDecodeError:
                        args = {}
                params = args if isinstance(args, dict) else {}

                try:
                    result = await gateway.invoke(name, params, envelope=envelope)
                except Exception as exc:
                    result = type("R", (), {"success": False, "output": {}, "error": str(exc)})()

                success = getattr(result, "success", False)
                output = getattr(result, "output", {})
                error = getattr(result, "error", "") or ""

                if success and name == "search_skill":
                    self._mount_skill_from_output(output)

                tool_content = json.dumps(
                    {"success": success, "output": output, "error": error} if not success
                    else {"success": True, "output": output},
                    ensure_ascii=False,
                )
                tool_msg = Message(role="tool", name=tool_call_id or name, content=tool_content)
                self._context.stm_add(tool_msg)

        return "(Reached max tool rounds without final reply.)"

    def _mount_skill_from_output(self, output: object) -> None:
        if not isinstance(output, dict):
            return
        skill_id = output.get("skill_id")
        name = output.get("name")
        content = output.get("content")
        description = output.get("description", "")
        if not isinstance(skill_id, str) or not skill_id.strip():
            return
        if not isinstance(name, str) or not name.strip():
            return
        if not isinstance(content, str) or not content.strip():
            prompt = output.get("prompt")
            if isinstance(prompt, str) and prompt.strip():
                content = prompt
            else:
                return
        if not isinstance(description, str):
            description = ""
        skill_path = output.get("skill_path")
        scripts = output.get("scripts")
        from pathlib import Path

        skill_dir = Path(skill_path) if isinstance(skill_path, str) and skill_path else None
        script_map: dict[str, Path] = {}
        if isinstance(scripts, dict):
            for key, value in scripts.items():
                if isinstance(key, str) and isinstance(value, str) and value:
                    script_map[key] = Path(value)
        from dare_framework.skill.types import Skill

        self._context.set_skill(
            Skill(
                id=skill_id.strip(),
                name=name.strip(),
                description=description.strip(),
                content=content,
                skill_dir=skill_dir,
                scripts=script_map,
            )
        )


__all__ = ["ReactAgent"]
