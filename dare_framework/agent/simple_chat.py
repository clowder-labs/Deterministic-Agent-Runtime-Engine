"""SimpleChatAgent - Simple chat agent implementation using Context.

A minimal agent for simple conversational interactions using the
context-centric architecture.
"""

from __future__ import annotations

from dare_framework.agent._internal.output_normalizer import build_output_envelope
from dare_framework.agent.base_agent import BaseAgent
from dare_framework.context import Context, Message
from dare_framework.model import IModelAdapter, ModelInput
from dare_framework.plan.types import RunResult
from dare_framework.tool import IToolGateway

from dare_framework.transport.kernel import AgentChannel


class SimpleChatAgent(BaseAgent):
    """Simple chat agent implementation using Context.

    This agent uses the context-centric architecture:
    - Context holds short-term memory, budget, and external references
    - Messages are assembled on-demand via Context.assemble()
    - Simple conversational flow without complex planning

    Example:
        agent = await (
            BaseAgent.simple_chat_agent_builder("chat-agent")
            .with_model(model)
            .build()
        )
        result = await agent("Hello, how are you?")
    """

    def __init__(
        self,
        name: str,
        *,
        model: IModelAdapter,
        context: Context,
        tool_gateway: IToolGateway,
        agent_channel: AgentChannel | None = None,
    ) -> None:
        """Initialize SimpleChatAgent.

        Args:
            name: Agent name identifier.
            model: Model adapter for generating responses (required).
            context: Pre-configured context (required, provided by builder).
            tool_gateway: Tool gateway used by Context for tool definitions.
            agent_channel: Optional transport channel for streaming outputs.
        """
        super().__init__(name, agent_channel=agent_channel)
        self._model = model
        self._context = context
        self._context.set_tool_gateway(tool_gateway)

    @property
    def context(self) -> Context:
        """Agent context."""
        return self._context

    async def execute(
        self,
        task: Message,
        *,
        transport: AgentChannel | None = None,
    ) -> RunResult:
        """Execute task using simple chat strategy.

        Flow:
        1. Add user message to short-term memory
        2. Assemble context (messages + tools)
        3. Call model to generate response
        4. Add assistant response to short-term memory
        5. Return model response content

        Args:
            task: Task description to execute.

        Returns:
            Normalized run result.
        """
        _ = transport
        self._context.stm_add(task)

        # 2. Assemble context for LLM call
        assembled = self._context.assemble()

        messages = list(assembled.messages)
        prompt_def = getattr(assembled, "sys_prompt", None)
        if prompt_def is not None:
            messages = [
                Message(
                    role=prompt_def.role,
                    text=prompt_def.content,
                    name=prompt_def.name,
                    metadata=dict(prompt_def.metadata),
                ),
                *messages,
            ]

        # 3. Convert to ModelInput format
        model_input = ModelInput(
            messages=messages,
            tools=assembled.tools,
            metadata=assembled.metadata,
        )

        # 4. Generate model response
        response = await self._model.generate(model_input)

        # 5. Add assistant response to short-term memory
        assistant_message = Message(role="assistant", text=response.content)
        self._context.stm_add(assistant_message)

        # 6. Record token usage if available
        if response.usage:
            tokens = response.usage.get("total_tokens", 0)
            if tokens:
                self._context.budget_use("tokens", tokens)

        # 7. Check budget
        self._context.budget_check()

        # 8. Return model response content
        output = build_output_envelope(response.content, usage=response.usage)
        return RunResult(
            success=True,
            output=output,
            output_text=output["content"],
        )


__all__ = ["SimpleChatAgent"]
