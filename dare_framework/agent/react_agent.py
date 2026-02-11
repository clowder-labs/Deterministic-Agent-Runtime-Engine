"""ReactAgent - Chat agent with ReAct tool loop (Reason → Act → Observe).

When the model returns tool_calls, this agent executes them, adds tool results
to context, and calls the model again until the model returns a final text response.
"""

from __future__ import annotations

import json

from dare_framework.agent.base_agent import BaseAgent
from dare_framework.context import Context, Message
from dare_framework.model import IModelAdapter, ModelInput
from dare_framework.plan.types import Envelope
from dare_framework.plan.types import RunResult
from dare_framework.plan.types import Task
from dare_framework.tool import IToolGateway, IToolProvider
from dare_framework.transport.kernel import AgentChannel


class ReactAgent(BaseAgent):
    """Chat agent that executes tool calls in a ReAct loop.

    Same context-centric setup as SimpleChatAgent, but when the model returns
    tool_calls, executes each tool via the injected tool gateway (e.g. ToolGateway),
    adds tool result messages to STM, reassembles, and calls the model again.
    Loops until the model returns no tool_calls, then returns that content.
    """

    def __init__(
        self,
        name: str,
        *,
        model: IModelAdapter,
        context: Context,
        tool_gateway: IToolGateway,
        plan_provider: IToolProvider | None = None,
        max_tool_rounds: int = 10,
        agent_channel: AgentChannel | None = None,
    ) -> None:
        super().__init__(name, agent_channel=agent_channel)
        self._model = model
        self._max_tool_rounds = max_tool_rounds
        self._context = context
        self._tool_gateway = tool_gateway
        self._plan_provider = plan_provider
        self._context.set_tool_gateway(self._tool_gateway)

    @property
    def context(self) -> Context:
        return self._context

    @property
    def plan_provider(self) -> IToolProvider | None:
        """Return optional mounted plan provider (if configured by builder)."""
        return self._plan_provider

    async def execute(
        self,
        task: str | Task,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        _ = transport
        task_description = task.description if isinstance(task, Task) else task
        user_message = Message(role="user", content=task_description)
        self._context.stm_add(user_message)

        gateway = self._tool_gateway

        for round_idx in range(self._max_tool_rounds):
            print(f"[{self.name}] Round {round_idx + 1}/{self._max_tool_rounds}: 调用模型中...", flush=True)
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
            # Inject critical_block from plan_provider (maintained by plan tools)
            if self._plan_provider is not None:
                state = getattr(self._plan_provider, "state", None)
                critical_block = getattr(state, "critical_block", "") if state else ""
                if critical_block:
                    print("\n--- [Plan State] (injected) ---\n" + critical_block + "\n---\n", flush=True)
                    messages.insert(
                        1,
                        Message(role="system", content=critical_block, name="plan_state"),
                    )

            model_input = ModelInput(
                messages=messages,
                tools=assembled.tools,
                metadata=assembled.metadata,
            )
            response = await self._model.generate(model_input)
            n_tools = len(response.tool_calls) if response.tool_calls else 0
            print(f"[{self.name}] 模型返回, tool_calls={n_tools}", flush=True)

            if response.usage:
                tokens = response.usage.get("total_tokens", 0)
                if tokens:
                    self._context.budget_use("tokens", tokens)
            self._context.budget_check()

            if not response.tool_calls:
                assistant_message = Message(role="assistant", content=response.content or "")
                self._context.stm_add(assistant_message)
                return RunResult(
                    success=True,
                    output=response.content or "",
                    output_text=response.content or "",
                )

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
                task_preview = (params.get("task") or "")[:80] if isinstance(params.get("task"), str) else ""
                print(f"[{self.name}] 执行工具: {name}" + (f" (task: {task_preview}...)" if task_preview else ""), flush=True)

                try:
                    result = await gateway.invoke(name, envelope=envelope, **params)
                except Exception as exc:
                    result = type("R", (), {"success": False, "output": {}, "error": str(exc)})()

                success = getattr(result, "success", False)
                output = getattr(result, "output", {})
                error = getattr(result, "error", "") or ""

                tool_content = json.dumps(
                    {"success": success, "output": output, "error": error} if not success
                    else {"success": True, "output": output},
                    ensure_ascii=False,
                )
                tool_msg = Message(role="tool", name=tool_call_id or name, content=tool_content)
                self._context.stm_add(tool_msg)

        final_message = "(Reached max tool rounds without final reply.)"
        return RunResult(
            success=True,
            output=final_message,
            output_text=final_message,
        )


__all__ = ["ReactAgent"]
