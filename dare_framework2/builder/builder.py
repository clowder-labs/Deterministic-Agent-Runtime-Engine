"""AgentBuilder - fluent builder for composing agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework2.config import Config
from dare_framework2.builder.agent import Agent
from dare_framework2.builder.types import PluginManagers
from dare_framework2.context.impl.default_context_manager import DefaultContextManager
from dare_framework2.execution.impl.default_extension_point import DefaultExtensionPoint
from dare_framework2.execution.impl.default_orchestrator import DefaultLoopOrchestrator
from dare_framework2.execution.impl.default_run_loop import DefaultRunLoop
from dare_framework2.execution.impl.file_execution_control import FileExecutionControl
from dare_framework2.execution.impl.in_memory_resource_manager import InMemoryResourceManager
from dare_framework2.execution.impl.local_event_log import LocalEventLog
from dare_framework2.execution.types import Budget
from dare_framework2.plan.impl.composite_validator import CompositeValidator
from dare_framework2.plan.impl.deterministic_planner import DeterministicPlanner
from dare_framework2.plan.impl.gateway_validator import GatewayValidator
from dare_framework2.plan.impl.noop_remediator import NoOpRemediator
from dare_framework2.tool.impl.default_security_boundary import DefaultSecurityBoundary
from dare_framework2.tool.impl.default_tool_gateway import DefaultToolGateway
from dare_framework2.tool.impl.edit_line_tool import EditLineTool
from dare_framework2.tool.impl.read_file_tool import ReadFileTool
from dare_framework2.tool.impl.native_tool_provider import NativeToolProvider
from dare_framework2.tool.impl.noop_tool import NoOpTool
from dare_framework2.tool.impl.protocol_adapter_provider import ProtocolAdapterProvider
from dare_framework2.tool.impl.run_context_state import RunContextState
from dare_framework2.tool.impl.search_code_tool import SearchCodeTool
from dare_framework2.tool.impl.write_file_tool import WriteFileTool

if TYPE_CHECKING:
    from dare_framework2.execution.interfaces import IEventLog, IHook
    from dare_framework2.memory.interfaces import IMemory
    from dare_framework2.model.interfaces import IModelAdapter
    from dare_framework2.plan.interfaces import IPlanner, IRemediator, IValidator
    from dare_framework2.tool.interfaces import ITool, IProtocolAdapter


class AgentBuilder:
    """Layer 3 builder for composing the Kernel and its pluggable components.
    
    Provides a fluent API for configuring and building Agent instances.
    
    Args:
        name: The agent name (used for event logs and checkpoints)
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._tools: list["ITool"] = []
        self._protocol_adapters: list["IProtocolAdapter"] = []
        self._plugin_managers: PluginManagers | None = None
        self._plugin_config: Config | None = None

        self._model_adapter: "IModelAdapter | None" = None
        self._planner: "IPlanner | None" = None
        self._validator: "IValidator | None" = None
        self._remediator: "IRemediator | None" = None
        self._memory: "IMemory | None" = None
        self._hooks: list["IHook"] = []

        self._budget = Budget(max_tool_calls=100, max_time_seconds=60)
        self._event_log: "IEventLog" = LocalEventLog(path=f".dare/{name}/event_log.jsonl")
        self._checkpoint_dir = f".dare/{name}/checkpoints"

    @classmethod
    def quick_start(cls, name: str) -> "AgentBuilder":
        """Create a minimal builder with Kernel defaults and a small toolset.
        
        Args:
            name: The agent name
            
        Returns:
            A pre-configured AgentBuilder
        """
        # Keep the default tool surface practical for local development and examples.
        # Higher-risk tools (like local command execution) should still be opt-in.
        return (
            cls(name)
            .with_kernel_defaults()
            .with_tools(
                NoOpTool(),
                ReadFileTool(),
                SearchCodeTool(),
                WriteFileTool(),
                EditLineTool(),
            )
        )

    def with_kernel_defaults(self) -> "AgentBuilder":
        """Enable Kernel defaults.
        
        The builder always targets the Kernelized architecture; this method
        exists to make the fluent API match the design docs.
        
        Returns:
            Self for chaining
        """
        return self

    def with_tools(self, *tools: "ITool") -> "AgentBuilder":
        """Add tools to the agent.
        
        Args:
            *tools: Tool instances to add
            
        Returns:
            Self for chaining
        """
        self._tools.extend(tools)
        return self

    def with_protocol(self, adapter: "IProtocolAdapter") -> "AgentBuilder":
        """Add a protocol adapter.
        
        Args:
            adapter: Protocol adapter instance
            
        Returns:
            Self for chaining
        """
        self._protocol_adapters.append(adapter)
        return self

    def with_hooks(self, *hooks: "IHook") -> "AgentBuilder":
        """Register hook components for the Kernel extension point.
        
        Args:
            *hooks: Hook instances to register
            
        Returns:
            Self for chaining
        """
        self._hooks.extend(hooks)
        return self

    def with_plugin_managers(
        self,
        managers: PluginManagers,
        *,
        config: Config | None = None,
    ) -> "AgentBuilder":
        """Attach plugin managers for entrypoint-driven composition.
        
        The builder remains usable without any plugin system: explicit
        `.with_*()` wiring is the primary path.
        
        Args:
            managers: Plugin managers container
            config: Optional configuration for plugin loading
            
        Returns:
            Self for chaining
        """
        self._plugin_managers = managers
        self._plugin_config = config
        return self

    def with_model(self, model: "IModelAdapter") -> "AgentBuilder":
        """Set the model adapter.
        
        Args:
            model: Model adapter instance
            
        Returns:
            Self for chaining
        """
        self._model_adapter = model
        return self

    def with_planner(self, planner: "IPlanner") -> "AgentBuilder":
        """Set the planner.
        
        Args:
            planner: Planner instance
            
        Returns:
            Self for chaining
        """
        self._planner = planner
        return self

    def with_validator(self, validator: "IValidator") -> "AgentBuilder":
        """Set the validator.
        
        Args:
            validator: Validator instance
            
        Returns:
            Self for chaining
        """
        self._validator = validator
        return self

    def with_remediator(self, remediator: "IRemediator") -> "AgentBuilder":
        """Set the remediator.
        
        Args:
            remediator: Remediator instance
            
        Returns:
            Self for chaining
        """
        self._remediator = remediator
        return self

    def with_memory(self, memory: "IMemory") -> "AgentBuilder":
        """Attach an optional memory component.
        
        Args:
            memory: Memory instance
            
        Returns:
            Self for chaining
        """
        self._memory = memory
        return self

    def with_budget(
        self,
        *,
        max_tokens: int | None = None,
        max_cost: float | None = None,
        max_time_seconds: int | None = None,
        max_tool_calls: int | None = None,
    ) -> "AgentBuilder":
        """Set the execution budget.
        
        Args:
            max_tokens: Maximum tokens allowed
            max_cost: Maximum cost allowed
            max_time_seconds: Maximum execution time
            max_tool_calls: Maximum tool invocations
            
        Returns:
            Self for chaining
        """
        self._budget = Budget(
            max_tokens=max_tokens,
            max_cost=max_cost,
            max_time_seconds=max_time_seconds,
            max_tool_calls=max_tool_calls,
        )
        return self

    def with_event_log(self, event_log: "IEventLog") -> "AgentBuilder":
        """Set the event log.
        
        Args:
            event_log: Event log instance
            
        Returns:
            Self for chaining
        """
        self._event_log = event_log
        return self

    def with_checkpoint_dir(self, path: str) -> "AgentBuilder":
        """Set the checkpoint directory.
        
        Args:
            path: Path to checkpoint directory
            
        Returns:
            Self for chaining
        """
        self._checkpoint_dir = path
        return self

    def build(self) -> Agent:
        """Build the Agent instance.
        
        Assembles all components and creates the final Agent.
        
        Returns:
            Configured Agent instance
        """
        plugin_validators: list["IValidator"] = []
        plugin_hooks: list["IHook"] = []

        # Load components from plugin managers if configured
        if self._plugin_managers is not None:
            self._load_from_plugin_managers(plugin_validators, plugin_hooks)

        # Always include a NoOp tool as a safe default
        if not any(tool.name == "noop" for tool in self._tools):
            self._tools.append(NoOpTool())

        run_context = RunContextState()
        # Carry the effective config snapshot into tool execution contexts so tools
        # can enforce workspace roots and guardrails deterministically.
        run_context.config = self._plugin_config

        # Build tool gateway
        tool_gateway = DefaultToolGateway()
        tool_gateway.register_provider(
            NativeToolProvider(tools=self._tools, context_factory=run_context.build)
        )
        for adapter in self._protocol_adapters:
            tool_gateway.register_provider(ProtocolAdapterProvider(adapter))

        # Build core components
        planner = self._planner or DeterministicPlanner([])
        if self._validator is not None:
            validator = self._validator
        else:
            base_validator: "IValidator" = GatewayValidator(tool_gateway)
            validator = (
                CompositeValidator([base_validator, *plugin_validators])
                if plugin_validators
                else base_validator
            )
        remediator = self._remediator or NoOpRemediator()

        # Build infrastructure
        resource_manager = InMemoryResourceManager(default_budget=self._budget)
        execution_control = FileExecutionControl(
            event_log=self._event_log,
            checkpoint_dir=self._checkpoint_dir,
        )
        security_boundary = DefaultSecurityBoundary()
        extension_point = DefaultExtensionPoint()
        
        # Register hooks
        for hook in [*self._hooks, *plugin_hooks]:
            extension_point.register_hook(hook.phase, hook)

        context_manager = DefaultContextManager(memory=self._memory)

        # Build orchestrator and run loop
        orchestrator = DefaultLoopOrchestrator(
            planner=planner,
            validator=validator,
            remediator=remediator,
            model_adapter=self._model_adapter,
            context_manager=context_manager,
            tool_gateway=tool_gateway,
            security_boundary=security_boundary,
            execution_control=execution_control,
            resource_manager=resource_manager,
            event_log=self._event_log,
            extension_point=extension_point,
            run_context_state=run_context,
        )
        run_loop = DefaultRunLoop(orchestrator)
        
        return Agent(run_loop=run_loop, run_context=run_context)

    def _load_from_plugin_managers(
        self,
        plugin_validators: list["IValidator"],
        plugin_hooks: list["IHook"],
    ) -> None:
        """Load components from plugin managers."""
        from dare_framework2.memory.interfaces import IMemory
        from dare_framework2.model.interfaces import IModelAdapter
        from dare_framework2.plan.interfaces import IPlanner, IRemediator, IValidator
        from dare_framework2.tool.interfaces import ITool, IProtocolAdapter
        from dare_framework2.execution.interfaces import IHook

        managers = self._plugin_managers
        if managers is None:
            return

        config = self._plugin_config

        if not self._tools and managers.tools is not None:
            discovered = managers.tools.load_tools(config=config)
            self._tools.extend([t for t in discovered if isinstance(t, ITool)])

        if self._model_adapter is None and managers.model_adapters is not None:
            candidate = managers.model_adapters.load_model_adapter(config=config)
            if isinstance(candidate, IModelAdapter):
                self._model_adapter = candidate

        if self._planner is None and managers.planners is not None:
            candidate = managers.planners.load_planner(config=config)
            if isinstance(candidate, IPlanner):
                self._planner = candidate

        if self._validator is None and managers.validators is not None:
            discovered = managers.validators.load_validators(config=config)
            plugin_validators.extend([v for v in discovered if isinstance(v, IValidator)])

        if self._remediator is None and managers.remediators is not None:
            candidate = managers.remediators.load_remediator(config=config)
            if isinstance(candidate, IRemediator):
                self._remediator = candidate

        if not self._protocol_adapters and managers.protocol_adapters is not None:
            discovered = managers.protocol_adapters.load_protocol_adapters(config=config)
            self._protocol_adapters.extend([a for a in discovered if isinstance(a, IProtocolAdapter)])

        if self._memory is None and managers.memory is not None:
            candidate = managers.memory.load_memory(config=config)
            if isinstance(candidate, IMemory):
                self._memory = candidate

        if managers.hooks is not None:
            discovered = managers.hooks.load_hooks(config=config)
            plugin_hooks.extend([h for h in discovered if isinstance(h, IHook)])
