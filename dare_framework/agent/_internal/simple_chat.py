"""SimpleChatAgent - Simple chat agent implementation using Context.

A minimal agent for simple conversational interactions using the
context-centric architecture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework.agent.base_agent import BaseAgent
from dare_framework.context import Context, Message
from dare_framework.model import IModelAdapter, ModelInput
from dare_framework.tool import IToolProvider
from dare_framework.compression import compress_context

if TYPE_CHECKING:
    from dare_framework.context import Budget
    from dare_framework.memory import IShortTermMemory, ILongTermMemory
    from dare_framework.knowledge import IKnowledge


class SimpleChatAgent(BaseAgent):
    """Simple chat agent implementation using Context.

    This agent uses the context-centric architecture:
    - Context holds short-term memory, budget, and external references
    - Messages are assembled on-demand via Context.assemble()
    - Simple conversational flow without complex planning

    Example:
        agent = SimpleChatAgent(
            name="chat-agent",
            model=model,
        )
        result = await agent.run("Hello, how are you?")
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
    ) -> None:
        """Initialize SimpleChatAgent.

        Args:
            name: Agent name identifier.
            model: Model adapter for generating responses (required).
            context: Pre-configured context (optional, will create default if not provided).
            short_term_memory: Short-term memory implementation (optional).
            long_term_memory: Long-term memory implementation (optional).
            knowledge: Knowledge retrieval implementation (optional).
            tools: Tool provider for listing tools (optional).
            budget: Resource budget (optional).
        """
        super().__init__(name)
        self._model = model

        # Create or use provided context
        if context is None:
            from dare_framework.context import Budget
            self._context = Context(
                id=f"context_{name}",
                short_term_memory=short_term_memory,
                long_term_memory=long_term_memory,
                knowledge=knowledge,
                budget=budget or Budget(),
            )
            # Set tool provider if provided
            if tools is not None:
                self._context._tool_provider = tools
        else:
            self._context = context

    @property
    def context(self) -> Context:
        """Agent context."""
        return self._context

    async def _execute(self, task: str) -> str:
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
            Model response content as string.
        """
        # 1. Add user message to short-term memory
        user_message = Message(role="user", content=task)
        self._context.stm_add(user_message)

        # 2. Compress context (lightweight, centralized strategy)
        compress_context(self._context, phase="simple_chat")

        # 3. Assemble context for LLM call
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

        # 4. Convert to ModelInput format
        model_input = ModelInput(
            messages=messages,
            tools=assembled.tools,
            metadata=assembled.metadata,
        )

        # 5. Generate model response
        response = await self._model.generate(model_input)

        # 6. Add assistant response to short-term memory
        assistant_message = Message(role="assistant", content=response.content)
        self._context.stm_add(assistant_message)

        # 7. Record token usage if available
        if response.usage:
            tokens = response.usage.get("total_tokens", 0)
            if tokens:
                self._context.budget_use("tokens", tokens)

        # 8. Check budget
        self._context.budget_check()

        # 9. Return model response content directly
        return response.content


__all__ = ["SimpleChatAgent"]
