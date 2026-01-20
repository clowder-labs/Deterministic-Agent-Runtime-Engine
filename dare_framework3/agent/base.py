"""BaseAgent - Abstract base class for all agent implementations.

BaseAgent provides the common infrastructure for all agents:
- Component assembly (tools, model, planner, etc.)
- Factory function calls to create default implementations
- Abstract _execute() method for subclasses to implement their execution logic

Users can either use predefined agents (FiveLayerAgent, SimpleChatAgent) or
inherit from BaseAgent to create fully custom execution strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from dare_framework3.plan.types import Task, RunResult

if TYPE_CHECKING:
    from dare_framework3.config.types import Config
    from dare_framework3.context.interfaces import IContextManager
    from dare_framework3.memory.interfaces import IMemory
    from dare_framework3.model.interfaces import IModelAdapter
    from dare_framework3.plan.interfaces import IPlanner, IValidator, IRemediator
    from dare_framework3.runtime.interfaces import (
        IExecutionControl,
        IResourceManager,
        IEventLog,
        IExtensionPoint,
        IHook,
    )
    from dare_framework3.runtime.types import Budget
    from dare_framework3.security.interfaces import ISecurityBoundary
    from dare_framework3.tool.interfaces import ITool, IToolGateway, IProtocolAdapter


class BaseAgent(ABC):
    """Abstract base class for all agent implementations.
    
    BaseAgent handles component assembly and provides the run() method.
    Subclasses must implement the _execute() method to define their
    specific execution strategy (e.g., five-layer loop, ReAct, etc.).
    
    Args:
        name: Agent identifier (used for event logs and checkpoints)
        model: Model adapter for LLM interactions (optional)
        tools: List of tools available to the agent
        protocol_adapters: Protocol adapters for external integrations (MCP, etc.)
        planner: Planning strategy implementation
        validator: Plan validation implementation
        remediator: Remediation strategy implementation
        memory: Memory component for context persistence
        hooks: Extension point hooks
        budget: Resource budget constraints
        config: Optional configuration object
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
        self._name = name
        self._config = config
        
        # Store user-provided components (may be None, defaults built later)
        self._user_model = model
        self._user_tools = tools or []
        self._user_protocol_adapters = protocol_adapters or []
        self._user_planner = planner
        self._user_validator = validator
        self._user_remediator = remediator
        self._user_memory = memory
        self._user_hooks = hooks or []
        self._user_budget = budget
        
        # Built components (lazy initialization)
        self._model: "IModelAdapter | None" = None
        self._tool_gateway: "IToolGateway | None" = None
        self._planner: "IPlanner | None" = None
        self._validator: "IValidator | None" = None
        self._remediator: "IRemediator | None" = None
        self._context_manager: "IContextManager | None" = None
        self._security_boundary: "ISecurityBoundary | None" = None
        self._execution_control: "IExecutionControl | None" = None
        self._resource_manager: "IResourceManager | None" = None
        self._event_log: "IEventLog | None" = None
        self._extension_point: "IExtensionPoint | None" = None
        
        # Run context for passing dependencies to tools
        self._run_context_state: Any = None
        self._deps: Any = None
        
        # Build all components
        self._build_components()

    @property
    def name(self) -> str:
        """Agent name identifier."""
        return self._name

    async def run(
        self,
        task: str | Task,
        deps: Any | None = None,
    ) -> RunResult:
        """Run a task and return the result.
        
        Args:
            task: The task to run (string description or Task object)
            deps: Optional dependencies to make available to tools
            
        Returns:
            The execution result
        """
        # Store deps for tool access (outside Task to keep Task serializable)
        self._deps = deps
        if self._run_context_state is not None:
            self._run_context_state.deps = deps
        
        # Convert string to Task if needed
        task_obj = task if isinstance(task, Task) else Task(description=task)
        
        # Delegate to subclass implementation
        return await self._execute(task_obj)

    @abstractmethod
    async def _execute(self, task: Task) -> RunResult:
        """Execute the task with the agent's specific strategy.
        
        Subclasses must implement this method to define their execution logic.
        This is where different agent types (five-layer, ReAct, etc.) diverge.
        
        Args:
            task: The task to execute
            
        Returns:
            The execution result
        """
        ...

    # =========================================================================
    # Component Building Methods (use factory functions to avoid DIP violation)
    # =========================================================================

    def _build_components(self) -> None:
        """Build all components using factory functions and user overrides."""
        # Import run context state (needed for tool execution)
        from dare_framework3.tool.impl.run_context_state import RunContextState
        self._run_context_state = RunContextState()
        
        # Build in dependency order
        self._model = self._user_model
        self._event_log = self._build_event_log()
        self._resource_manager = self._build_resource_manager()
        self._execution_control = self._build_execution_control()
        self._extension_point = self._build_extension_point()
        self._tool_gateway = self._build_tool_gateway()
        self._security_boundary = self._build_security_boundary()
        self._context_manager = self._build_context_manager()
        self._planner = self._build_planner()
        self._validator = self._build_validator()
        self._remediator = self._build_remediator()
        
        # Register hooks
        self._register_hooks()

    def _build_event_log(self) -> "IEventLog":
        """Build event log using factory function."""
        from dare_framework3.runtime import create_default_event_log
        return create_default_event_log(path=f".dare/{self._name}/event_log.jsonl")

    def _build_resource_manager(self) -> "IResourceManager":
        """Build resource manager using factory function."""
        from dare_framework3.runtime import create_default_resource_manager
        budget = self._user_budget
        if budget is None:
            from dare_framework3.runtime.types import Budget
            budget = Budget(max_tool_calls=100, max_time_seconds=60)
        return create_default_resource_manager(budget=budget)

    def _build_execution_control(self) -> "IExecutionControl":
        """Build execution control using factory function."""
        from dare_framework3.runtime import create_default_execution_control
        return create_default_execution_control(
            event_log=self._event_log,
            checkpoint_dir=f".dare/{self._name}/checkpoints",
        )

    def _build_extension_point(self) -> "IExtensionPoint":
        """Build extension point using factory function."""
        from dare_framework3.runtime import create_default_extension_point
        return create_default_extension_point()

    def _build_tool_gateway(self) -> "IToolGateway":
        """Build tool gateway using factory function."""
        from dare_framework3.tool import create_default_tool_gateway
        from dare_framework3.tool.impl.native_tool_provider import NativeToolProvider
        from dare_framework3.tool.impl.protocol_adapter_provider import ProtocolAdapterProvider
        from dare_framework3.tool.impl.noop_tool import NoOpTool
        
        gateway = create_default_tool_gateway()
        
        # Ensure at least one tool exists
        tools = list(self._user_tools)
        if not any(getattr(t, "name", None) == "noop" for t in tools):
            tools.append(NoOpTool())
        
        # Register native tools
        gateway.register_provider(
            NativeToolProvider(tools=tools, context_factory=self._run_context_state.build)
        )
        
        # Register protocol adapters
        for adapter in self._user_protocol_adapters:
            gateway.register_provider(ProtocolAdapterProvider(adapter))
        
        return gateway

    def _build_security_boundary(self) -> "ISecurityBoundary":
        """Build security boundary using factory function."""
        from dare_framework3.security import create_default_security_boundary
        return create_default_security_boundary()

    def _build_context_manager(self) -> "IContextManager":
        """Build context manager using factory function."""
        from dare_framework3.context import create_default_context_manager
        return create_default_context_manager(memory=self._user_memory)

    def _build_planner(self) -> "IPlanner":
        """Build planner using factory function or user override."""
        if self._user_planner is not None:
            return self._user_planner
        from dare_framework3.plan import create_default_planner
        return create_default_planner()

    def _build_validator(self) -> "IValidator":
        """Build validator using factory function or user override."""
        if self._user_validator is not None:
            return self._user_validator
        from dare_framework3.plan import create_default_validator
        return create_default_validator(tool_gateway=self._tool_gateway)

    def _build_remediator(self) -> "IRemediator":
        """Build remediator using factory function or user override."""
        if self._user_remediator is not None:
            return self._user_remediator
        from dare_framework3.plan import create_default_remediator
        return create_default_remediator()

    def _register_hooks(self) -> None:
        """Register user-provided hooks with the extension point."""
        if self._extension_point is None:
            return
        for hook in self._user_hooks:
            self._extension_point.register_hook(hook.phase, hook)
