from __future__ import annotations

from typing import Any

from dare_framework.components.hooks.protocols import IHook
from dare_framework.contracts.memory import IMemory
from dare_framework.components.planners.deterministic import DeterministicPlanner
from dare_framework.components.providers.native_tool_provider import NativeToolProvider
from dare_framework.components.providers.protocol_adapter_provider import ProtocolAdapterProvider
from dare_framework.components.remediators import NoOpRemediator
from dare_framework.components.tools.noop import NoOpTool
from dare_framework.components.validators.composite import CompositeValidator
from dare_framework.components.validators.kernel_validator import GatewayValidator
from dare_framework.contracts.model import IModelAdapter
from dare_framework.contracts.tool import ITool
from dare_framework.core.budget import Budget
from dare_framework.core.budget.in_memory import InMemoryResourceManager
from dare_framework.core.context.default_context_manager import DefaultContextManager
from dare_framework.core.execution_control.file_execution_control import FileExecutionControl
from dare_framework.core.event.local_event_log import LocalEventLog
from dare_framework.core.hook.default_extension_point import DefaultExtensionPoint
from dare_framework.core.orchestrator.default_orchestrator import DefaultLoopOrchestrator
from dare_framework.core.run_loop.default_run_loop import DefaultRunLoop
from dare_framework.core.security.default_security_boundary import DefaultSecurityBoundary
from dare_framework.core.tool.default_tool_gateway import DefaultToolGateway
from dare_framework.core.tool.run_context_state import RunContextState
from dare_framework.core.event import IEventLog
from dare_framework.core.protocols import IPlanner, IRemediator, IValidator
from dare_framework.core.plan.results import RunResult
from dare_framework.core.run_loop import IRunLoop
from dare_framework.core.plan.task import Task
from dare_framework.protocols.base import IProtocolAdapter
from dare_framework.components.plugin_system.managers import PluginManagers


class Agent:
    """Developer-facing agent wrapper around the v2 Kernel run loop."""

    def __init__(self, *, run_loop: IRunLoop, run_context: RunContextState) -> None:
        self._run_loop = run_loop
        self._run_context = run_context

    async def run(self, task: str | Task, deps: Any | None = None) -> RunResult:
        # deps is intentionally stored outside Task to keep Task serializable and audit-friendly.
        self._run_context.deps = deps
        task_obj = task if isinstance(task, Task) else Task(description=task)
        return await self._run_loop.run(task_obj)


class AgentBuilder:
    """Layer 3 builder for composing the v2 Kernel and its pluggable components."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._tools: list[ITool] = []
        self._protocol_adapters: list[IProtocolAdapter] = []
        self._plugin_managers: PluginManagers | None = None
        self._plugin_config: Any | None = None

        self._model_adapter: IModelAdapter | None = None
        self._planner: IPlanner | None = None
        self._validator: IValidator | None = None
        self._remediator: IRemediator | None = None
        self._memory: IMemory | None = None
        self._hooks: list[IHook] = []

        self._budget = Budget(max_tool_calls=100, max_time_seconds=60)
        self._event_log: IEventLog = LocalEventLog(path=f".dare/{name}/event_log.jsonl")
        self._checkpoint_dir = f".dare/{name}/checkpoints"

    @classmethod
    def quick_start(cls, name: str) -> "AgentBuilder":
        """Minimal builder with Kernel defaults and a NoOp tool."""

        return cls(name).with_kernel_defaults().with_tools(NoOpTool())

    def with_kernel_defaults(self) -> "AgentBuilder":
        """Enable Kernel defaults (v2.0).

        The v2 builder always targets the Kernelized architecture; this method exists to make
        the fluent API match the v2.0 design docs.
        """

        return self

    def with_tools(self, *tools: ITool) -> "AgentBuilder":
        self._tools.extend(tools)
        return self

    def with_protocol(self, adapter: IProtocolAdapter) -> "AgentBuilder":
        self._protocol_adapters.append(adapter)
        return self

    def with_hooks(self, *hooks: IHook) -> "AgentBuilder":
        """Register hook components to be installed into the Kernel extension point."""

        self._hooks.extend(hooks)
        return self

    def with_plugin_managers(self, managers: PluginManagers, *, config: Any | None = None) -> "AgentBuilder":
        """Attach plugin managers for entrypoint-driven composition (v2).

        This builder remains usable without any plugin system: explicit `.with_*()`
        wiring is the primary MVP path. Managers exist as interface positions so the
        framework can later support deterministic entrypoint discovery + config-driven
        selection without coupling the Kernel to `importlib.metadata`.
        """

        self._plugin_managers = managers
        self._plugin_config = config
        return self

    def with_model(self, model: IModelAdapter) -> "AgentBuilder":
        self._model_adapter = model
        return self

    def with_planner(self, planner: IPlanner) -> "AgentBuilder":
        self._planner = planner
        return self

    def with_validator(self, validator: IValidator) -> "AgentBuilder":
        self._validator = validator
        return self

    def with_remediator(self, remediator: IRemediator) -> "AgentBuilder":
        self._remediator = remediator
        return self

    def with_memory(self, memory: IMemory) -> "AgentBuilder":
        """Attach an optional memory component used by the default context manager."""

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
        self._budget = Budget(
            max_tokens=max_tokens,
            max_cost=max_cost,
            max_time_seconds=max_time_seconds,
            max_tool_calls=max_tool_calls,
        )
        return self

    def with_event_log(self, event_log: IEventLog) -> "AgentBuilder":
        self._event_log = event_log
        return self

    def with_checkpoint_dir(self, path: str) -> "AgentBuilder":
        self._checkpoint_dir = path
        return self

    def build(self) -> Agent:
        plugin_validators: list[IValidator] = []
        plugin_hooks: list[IHook] = []

        if self._plugin_managers is not None:
            if not self._tools and self._plugin_managers.tools is not None:
                discovered = self._plugin_managers.tools.load_tools(config=self._plugin_config)
                self._tools.extend([tool for tool in discovered if isinstance(tool, ITool)])
            if self._model_adapter is None and self._plugin_managers.model_adapters is not None:
                candidate = self._plugin_managers.model_adapters.load_model_adapter(config=self._plugin_config)
                if isinstance(candidate, IModelAdapter):
                    self._model_adapter = candidate
            if self._planner is None and self._plugin_managers.planners is not None:
                candidate = self._plugin_managers.planners.load_planner(config=self._plugin_config)
                if isinstance(candidate, IPlanner):
                    self._planner = candidate
            if self._validator is None and self._plugin_managers.validators is not None:
                discovered = self._plugin_managers.validators.load_validators(config=self._plugin_config)
                plugin_validators = [item for item in discovered if isinstance(item, IValidator)]
            if self._remediator is None and self._plugin_managers.remediators is not None:
                candidate = self._plugin_managers.remediators.load_remediator(config=self._plugin_config)
                if isinstance(candidate, IRemediator):
                    self._remediator = candidate
            if not self._protocol_adapters and self._plugin_managers.protocol_adapters is not None:
                discovered = self._plugin_managers.protocol_adapters.load_protocol_adapters(config=self._plugin_config)
                self._protocol_adapters.extend([item for item in discovered if isinstance(item, IProtocolAdapter)])
            if self._memory is None and self._plugin_managers.memory is not None:
                candidate = self._plugin_managers.memory.load_memory(config=self._plugin_config)
                if isinstance(candidate, IMemory):
                    self._memory = candidate
            if self._plugin_managers.hooks is not None:
                discovered = self._plugin_managers.hooks.load_hooks(config=self._plugin_config)
                plugin_hooks = [item for item in discovered if isinstance(item, IHook)]

        # Always include a NoOp tool as a safe default so the Kernel can run even when the
        # planner is configured with an empty plan (or when model-driven execution is used).
        if not any(tool.name == "noop" for tool in self._tools):
            self._tools.append(NoOpTool())

        run_context = RunContextState()

        tool_gateway = DefaultToolGateway()
        tool_gateway.register_provider(NativeToolProvider(tools=self._tools, context_factory=run_context.build))
        for adapter in self._protocol_adapters:
            tool_gateway.register_provider(ProtocolAdapterProvider(adapter))

        planner = self._planner or DeterministicPlanner([])
        if self._validator is not None:
            validator = self._validator
        else:
            base_validator: IValidator = GatewayValidator(tool_gateway)
            validator = CompositeValidator([base_validator, *plugin_validators]) if plugin_validators else base_validator
        remediator = self._remediator or NoOpRemediator()

        resource_manager = InMemoryResourceManager(default_budget=self._budget)
        execution_control = FileExecutionControl(event_log=self._event_log, checkpoint_dir=self._checkpoint_dir)
        security_boundary = DefaultSecurityBoundary()
        extension_point = DefaultExtensionPoint()
        for hook in [*self._hooks, *plugin_hooks]:
            extension_point.register_hook(hook.phase, hook)

        context_manager = DefaultContextManager(memory=self._memory)

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
        run_loop: IRunLoop = DefaultRunLoop(orchestrator)
        return Agent(run_loop=run_loop, run_context=run_context)
