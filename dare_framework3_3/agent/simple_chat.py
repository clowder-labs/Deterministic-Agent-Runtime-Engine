"""SimpleChatAgent - Simple chat agent implementation.

A minimal agent for simple conversational interactions.
This is a placeholder for future implementation.

SimpleChatAgent is suitable for:
- Simple Q&A interactions
- Conversations without complex planning
- Use cases where full five-layer orchestration is unnecessary
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework3_3.agent.base import BaseAgent
from dare_framework3_3.plan.types import Task, RunResult, SessionSummary

if TYPE_CHECKING:
    from dare_framework3_3.config.types import Config
    from dare_framework3_3.memory.component import IMemory
    from dare_framework3_3.model.component import IModelAdapter
    from dare_framework3_3.plan.component import IPlanner, IValidator, IRemediator
    from dare_framework3_3.hook.component import IHook
    from dare_framework3_3.context.types import Budget
    from dare_framework3_3.tool.component import ITool, IProtocolAdapter


class SimpleChatAgent(BaseAgent):
    """Simple chat agent implementation.
    
    [PLACEHOLDER] This agent is intended for simple conversational use cases
    where the full five-layer orchestration is not needed.
    
    Current implementation is a stub that returns a placeholder result.
    Future implementation will support:
    - Direct model invocation without planning
    - Simple tool calling
    - Conversation history management
    
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
        model: "IModelAdapter | None" = None,
        tools: list["ITool"] | None = None,
        protocol_adapters: list["IProtocolAdapter"] | None = None,
        planner: "IPlanner | None" = None,
        validator: "IValidator | None" = None,
        remediator: "IRemediator | None" = None,
        memory: "IMemory | None" = None,
        hooks: list["IHook"] | None = None,
        budget: "Budget | None" = None,
        config: "Config | None" = None,
    ) -> None:
        super().__init__(
            name,
            model=model,
            tools=tools,
            protocol_adapters=protocol_adapters,
            planner=planner,
            validator=validator,
            remediator=remediator,
            memory=memory,
            hooks=hooks,
            budget=budget,
            config=config,
        )

    async def _execute(self, task: Task) -> RunResult:
        """Execute task using simple chat strategy.
        
        [PLACEHOLDER] Current implementation returns a stub result.
        Future implementation will:
        1. Send task description directly to model
        2. Handle tool calls if any
        3. Return model response
        """
        # Placeholder implementation - just return a stub result
        return RunResult(
            success=True,
            output=None,
            milestone_results=[],
            errors=[],
            session_summary=SessionSummary(
                session_id=f"simple_chat_{task.task_id}",
                milestone_count=0,
                success=True,
            ),
        )
