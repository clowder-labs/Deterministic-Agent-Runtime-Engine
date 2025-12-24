from __future__ import annotations

from typing import Generic, TypeVar

from .components.context_assembler import BasicContextAssembler
from .components.defaults import (
    AllowAllPolicyEngine,
    DeterministicPlanGenerator,
    InMemoryMemory,
    MockModelAdapter,
    NoOpHook,
    NoOpRemediator,
    NoOpTool,
    SimpleValidator,
)
from .components.mcp_toolkit import MCPToolkit
from .components.registries import SkillRegistry, ToolRegistry
from .components.tool_runtime import ToolRuntime
from .core.interfaces import (
    IAgent,
    ICheckpoint,
    IContextAssembler,
    IEventLog,
    IModelAdapter,
    IPlanGenerator,
    IPolicyEngine,
    IRemediator,
    IRuntime,
    IValidator,
)
from .core.models import PlanStep, RunResult, Task, new_id
from .core.runtime import AgentRuntime

DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")


class Agent(IAgent[DepsT, OutputT]):
    def __init__(self, runtime: IRuntime[DepsT, OutputT]) -> None:
        self._runtime = runtime

    async def run(self, task: Task, deps: DepsT) -> RunResult[OutputT]:
        await self._runtime.init(task)
        return await self._runtime.run(task, deps)


class AgentBuilder(Generic[DepsT, OutputT]):
    def __init__(self, name: str) -> None:
        self._name = name
        self._tool_registry = ToolRegistry()
        self._skill_registry = SkillRegistry()
        self._model_adapter: IModelAdapter | None = None
        self._memory = InMemoryMemory()
        self._hooks = [NoOpHook()]
        self._plan_generator: IPlanGenerator | None = None
        self._validator: IValidator | None = None
        self._policy_engine: IPolicyEngine | None = None
        self._remediator: IRemediator | None = None
        self._context_assembler: IContextAssembler | None = None
        self._event_log: IEventLog | None = None
        self._checkpoint: ICheckpoint | None = None
        self._runtime: IRuntime | None = None
        self._mcp_clients = []

    @classmethod
    def quick_start(cls, name: str, model: str | None = None) -> "AgentBuilder":
        builder = cls(name)
        builder._model_adapter = MockModelAdapter([model or "ok"])
        builder.with_tools(NoOpTool())
        builder._plan_generator = DeterministicPlanGenerator(
            [[PlanStep(step_id=new_id("step"), tool_name="noop", tool_input={})]]
        )
        return builder

    def description(self, text: str) -> "AgentBuilder":
        self._name = text
        return self

    def with_tools(self, *tools) -> "AgentBuilder":
        self._tool_registry.register_many(tools)
        return self

    def with_skills(self, *skills) -> "AgentBuilder":
        self._skill_registry.register_many(skills)
        return self

    def with_model(self, model: IModelAdapter) -> "AgentBuilder":
        self._model_adapter = model
        return self

    def with_memory(self, memory) -> "AgentBuilder":
        self._memory = memory
        return self

    def with_hook(self, hook) -> "AgentBuilder":
        self._hooks.append(hook)
        return self

    def with_runtime(self, runtime: IRuntime) -> "AgentBuilder":
        self._runtime = runtime
        return self

    def with_plan_generator(self, plan_generator: IPlanGenerator) -> "AgentBuilder":
        self._plan_generator = plan_generator
        return self

    def with_validator(self, validator: IValidator) -> "AgentBuilder":
        self._validator = validator
        return self

    def with_policy_engine(self, policy_engine: IPolicyEngine) -> "AgentBuilder":
        self._policy_engine = policy_engine
        return self

    def with_remediator(self, remediator: IRemediator) -> "AgentBuilder":
        self._remediator = remediator
        return self

    def with_context_assembler(self, context_assembler: IContextAssembler) -> "AgentBuilder":
        self._context_assembler = context_assembler
        return self

    def with_event_log(self, event_log: IEventLog) -> "AgentBuilder":
        self._event_log = event_log
        return self

    def with_checkpoint(self, checkpoint: ICheckpoint) -> "AgentBuilder":
        self._checkpoint = checkpoint
        return self

    def with_mcp(self, *clients) -> "AgentBuilder":
        self._mcp_clients.extend(clients)
        return self

    def build(self) -> Agent[DepsT, OutputT]:
        if self._mcp_clients:
            raise RuntimeError("MCP clients require build_async() for initialization")
        return self._build()

    async def build_async(self) -> Agent[DepsT, OutputT]:
        if self._runtime is not None:
            return Agent(self._runtime)
        if self._mcp_clients:
            mcp_toolkit = MCPToolkit(self._mcp_clients)
            await mcp_toolkit.initialize()
            for tool in mcp_toolkit.export_tools():
                self._tool_registry.register_tool(tool)
        return self._build()

    def _build(self) -> Agent[DepsT, OutputT]:
        if self._runtime is not None:
            return Agent(self._runtime)
        validator = self._validator or SimpleValidator()
        policy_engine = self._policy_engine or AllowAllPolicyEngine()
        remediator = self._remediator or NoOpRemediator()
        context_assembler = self._context_assembler or BasicContextAssembler()
        if self._plan_generator is None:
            if self._tool_registry.get_tool("noop") is None:
                self._tool_registry.register_tool(NoOpTool())
            plan_generator = DeterministicPlanGenerator(
                [[PlanStep(step_id=new_id("step"), tool_name="noop", tool_input={})]]
            )
        else:
            plan_generator = self._plan_generator

        tool_runtime = ToolRuntime(
            toolkit=self._tool_registry,
            skill_registry=self._skill_registry,
            policy_engine=policy_engine,
            validator=validator,
        )
        runtime = AgentRuntime(
            tool_runtime=tool_runtime,
            plan_generator=plan_generator,
            validator=validator,
            policy_engine=policy_engine,
            remediator=remediator,
            context_assembler=context_assembler,
            event_log=self._event_log,
            checkpoint=self._checkpoint,
        )
        return Agent(runtime)
