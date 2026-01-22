"""BaseAgent - abstract base class for agent implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from dare_framework3_3.plan.types import Task, RunResult

if TYPE_CHECKING:
    from dare_framework3_3.config.types import Config
    from dare_framework3_3.context.kernel import IContextManager, IResourceManager
    from dare_framework3_3.context.types import Budget
    from dare_framework3_3.event.kernel import IEventLog
    from dare_framework3_3.hook.kernel import IExtensionPoint
    from dare_framework3_3.hook.component import IHook
    from dare_framework3_3.memory.component import IMemory
    from dare_framework3_3.model.component import IModelAdapter
    from dare_framework3_3.plan.component import IPlanner, IValidator, IRemediator
    from dare_framework3_3.security.kernel import ISecurityBoundary
    from dare_framework3_3.tool.kernel import IToolGateway, IExecutionControl
    from dare_framework3_3.tool.component import ITool, IProtocolAdapter


class BaseAgent(ABC):
    """Abstract base class for all agent implementations."""

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
        event_log: "IEventLog | None" = None,
        resource_manager: "IResourceManager | None" = None,
        execution_control: "IExecutionControl | None" = None,
        extension_point: "IExtensionPoint | None" = None,
        context_manager: "IContextManager | None" = None,
        security_boundary: "ISecurityBoundary | None" = None,
        tool_gateway: "IToolGateway | None" = None,
    ) -> None:
        self._name = name
        self._config = config

        self._user_model = model
        self._user_tools = tools or []
        self._user_protocol_adapters = protocol_adapters or []
        self._user_planner = planner
        self._user_validator = validator
        self._user_remediator = remediator
        self._user_memory = memory
        self._user_hooks = hooks or []
        self._user_budget = budget
        self._user_event_log = event_log
        self._user_resource_manager = resource_manager
        self._user_execution_control = execution_control
        self._user_extension_point = extension_point
        self._user_context_manager = context_manager
        self._user_security_boundary = security_boundary
        self._user_tool_gateway = tool_gateway

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

        self._run_context_state: Any = None
        self._deps: Any = None

        self._build_components()

    @property
    def name(self) -> str:
        return self._name

    async def run(self, task: str | Task, deps: Any | None = None) -> RunResult:
        self._deps = deps
        if self._run_context_state is not None:
            self._run_context_state.deps = deps
        task_obj = task if isinstance(task, Task) else Task(description=task)
        return await self._execute(task_obj)

    @abstractmethod
    async def _execute(self, task: Task) -> RunResult:
        ...

    def _build_components(self) -> None:
        from dare_framework3_3.tool.internal.run_context_state import RunContextState

        self._run_context_state = RunContextState()

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

        self._register_hooks()

    def _build_event_log(self) -> "IEventLog":
        from dare_framework3_3.event.internal.local_event_log import LocalEventLog

        return self._user_event_log or LocalEventLog(path=f".dare/{self._name}/event_log.jsonl")

    def _build_resource_manager(self) -> "IResourceManager":
        from dare_framework3_3.context.internal.in_memory_resource_manager import InMemoryResourceManager
        from dare_framework3_3.context.types import Budget

        if self._user_resource_manager is not None:
            return self._user_resource_manager

        budget = self._user_budget or Budget(max_tool_calls=100, max_time_seconds=60)
        return InMemoryResourceManager(default_budget=budget)

    def _build_execution_control(self) -> "IExecutionControl":
        from dare_framework3_3.tool.internal.file_execution_control import FileExecutionControl

        if self._user_execution_control is not None:
            return self._user_execution_control

        return FileExecutionControl(
            event_log=self._event_log,
            checkpoint_dir=f".dare/{self._name}/checkpoints",
        )

    def _build_extension_point(self) -> "IExtensionPoint":
        from dare_framework3_3.hook.internal.default_extension_point import DefaultExtensionPoint

        return self._user_extension_point or DefaultExtensionPoint()

    def _build_tool_gateway(self) -> "IToolGateway":
        from dare_framework3_3.tool.internal.default_tool_gateway import DefaultToolGateway
        from dare_framework3_3.tool.internal.native_tool_provider import NativeToolProvider
        from dare_framework3_3.tool.internal.protocol_adapter_provider import ProtocolAdapterProvider
        from dare_framework3_3.tool.internal.noop_tool import NoOpTool

        if self._user_tool_gateway is not None:
            return self._user_tool_gateway

        gateway = DefaultToolGateway()

        tools = list(self._user_tools)
        if not any(getattr(t, "name", None) == "noop" for t in tools):
            tools.append(NoOpTool())

        gateway.register_provider(
            NativeToolProvider(tools=tools, context_factory=self._run_context_state.build)
        )

        for adapter in self._user_protocol_adapters:
            gateway.register_provider(ProtocolAdapterProvider(adapter))

        return gateway

    def _build_security_boundary(self) -> "ISecurityBoundary":
        from dare_framework3_3.security.internal.default_security_boundary import DefaultSecurityBoundary

        return self._user_security_boundary or DefaultSecurityBoundary()

    def _build_context_manager(self) -> "IContextManager":
        from dare_framework3_3.context.internal.default_context_manager import DefaultContextManager
        from dare_framework3_3.config import DefaultConfigProvider

        config_provider = DefaultConfigProvider(self._config) if self._config is not None else DefaultConfigProvider()
        return self._user_context_manager or DefaultContextManager(
            memory=self._user_memory,
            config_provider=config_provider,
            tool_gateway=self._tool_gateway,
        )

    def _build_planner(self) -> "IPlanner":
        if self._user_planner is not None:
            return self._user_planner
        from dare_framework3_3.plan.internal.deterministic_planner import DeterministicPlanner

        return DeterministicPlanner(plans=[])

    def _build_validator(self) -> "IValidator":
        if self._user_validator is not None:
            return self._user_validator
        from dare_framework3_3.plan.internal.composite_validator import CompositeValidator
        from dare_framework3_3.plan.internal.gateway_validator import GatewayValidator

        return CompositeValidator([GatewayValidator(self._tool_gateway)])

    def _build_remediator(self) -> "IRemediator":
        if self._user_remediator is not None:
            return self._user_remediator
        from dare_framework3_3.plan.internal.noop_remediator import NoOpRemediator

        return NoOpRemediator()

    def _register_hooks(self) -> None:
        if self._extension_point is None:
            return
        for hook in self._user_hooks:
            self._extension_point.register_hook(hook.phase, hook)
