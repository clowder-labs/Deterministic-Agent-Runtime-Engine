"""SimpleChatAgent - Simple chat agent implementation using v3.4 Context.

A minimal agent for simple conversational interactions using the v3.4
context-centric architecture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework3_4.agent.base import BaseAgent
from dare_framework3_4.context import Context, Message
from dare_framework3_4.model import IModelAdapter, Prompt
from dare_framework3_4.plan import Task, RunResult, SessionSummary
from dare_framework3_4.tool import IToolProvider
from dare_framework3_4.tool.types import ToolResult

if TYPE_CHECKING:
    from dare_framework3_4.context import Budget
    from dare_framework3_4.memory import IShortTermMemory, ILongTermMemory
    from dare_framework3_4.knowledge import IKnowledge


class SimpleChatAgent(BaseAgent):
    """Simple chat agent implementation using v3.4 Context.

    This agent uses the v3.4 context-centric architecture:
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
        short_term_memory: "IShortTermMemory | None" = None,
        long_term_memory: "ILongTermMemory | None" = None,
        knowledge: "IKnowledge | None" = None,
        tools: "IToolProvider | None" = None,
        budget: "Budget | None" = None,
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
            from dare_framework3_4.context import Budget
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

    async def _execute(self, task: Task) -> RunResult:
        """Execute task using simple chat strategy.

        Flow:
        1. Add user message to short-term memory
        2. Assemble context (messages + tools)
        3. Call model to generate response
        4. Add assistant response to short-term memory
        5. Return result

        Args:
            task: Task to execute.

        Returns:
            RunResult with model response.
        """
        try:
            # 1. Add user message to short-term memory
            user_message = Message(role="user", content=task.description)
            self._context.stm_add(user_message)

            # 2. Assemble context for LLM call
            assembled = self._context.assemble()

            # 3. Convert to Prompt format
            prompt = Prompt(
                messages=assembled.messages,
                tools=assembled.tools,
                metadata=assembled.metadata,
            )

            # 4. Generate model response
            response = await self._model.generate(prompt)

            # 5. Add assistant response to short-term memory
            assistant_message = Message(role="assistant", content=response.content)
            self._context.stm_add(assistant_message)

            # 6. Record token usage if available
            if response.usage:
                tokens = response.usage.get("total_tokens", 0)
                if tokens:
                    self._context.budget_use("tokens", tokens)

            # 7. Check budget
            self._context.budget_check()

            # 8. Create ToolResult for compatibility with 3.2 format
            # 3.2 expects result.output to be a list of ToolResult objects
            tool_result = ToolResult(
                success=True,
                output={"content": response.content},
            )

            # 9. Return result (compatible with 3.2 format)
            return RunResult(
                success=True,
                output=[tool_result],  # List format for 3.2 compatibility
                errors=[],
                session_summary=SessionSummary(
                    session_id=f"session_{task.task_id}",
                    milestone_count=1,
                    success=True,
                ),
            )

        except Exception as e:
            return RunResult(
                success=False,
                output=None,
                errors=[str(e)],
                session_summary=SessionSummary(
                    session_id=f"session_{task.task_id}",
                    milestone_count=1,
                    success=False,
                ),
            )


__all__ = ["SimpleChatAgent"]
