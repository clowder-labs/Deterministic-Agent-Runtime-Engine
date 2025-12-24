from __future__ import annotations

from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from .models import (
    AssembledContext,
    DonePredicate,
    Envelope,
    Evidence,
    Event,
    EventFilter,
    GenerateOptions,
    Message,
    MemoryItem,
    Milestone,
    MilestoneContext,
    ModelResponse,
    PolicyDecision,
    ProposedPlan,
    ProposedStep,
    Resource,
    ResourceContent,
    RunContext,
    RunResult,
    RuntimeSnapshot,
    RuntimeState,
    Task,
    ToolDefinition,
    ToolResult,
    ToolType,
    ValidationResult,
    ValidatedPlan,
    VerifyResult,
)

DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")


@runtime_checkable
class IComponentRegistrar(Protocol):
    def register_component(self, component: "IComponent") -> None:
        ...


@runtime_checkable
class IComponent(Protocol):
    @property
    def order(self) -> int:
        ...

    async def init(self, config: "IConfigProvider | None" = None, prompts: "IPromptStore | None" = None) -> None:
        ...

    def register(self, registrar: IComponentRegistrar) -> None:
        ...

    async def close(self) -> None:
        ...


class IRuntime(Protocol, Generic[DepsT, OutputT]):
    async def init(self, task: Task) -> None:
        ...

    async def run(self, task: Task, deps: DepsT) -> RunResult[OutputT]:
        ...

    async def pause(self) -> None:
        ...

    async def resume(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    async def cancel(self) -> None:
        ...

    def get_state(self) -> RuntimeState:
        ...


class IEventLog(Protocol):
    async def append(self, event: Event) -> str:
        ...

    async def query(self, filter: EventFilter | None = None, offset: int = 0, limit: int = 100) -> list[Event]:
        ...

    async def verify_chain(self) -> bool:
        ...

    async def get_checkpoint_events(self, checkpoint_id: str) -> list[Event]:
        ...


class ICheckpoint(Protocol):
    async def save(self, snapshot: RuntimeSnapshot) -> str:
        ...

    async def load(self, checkpoint_id: str) -> RuntimeSnapshot:
        ...


@runtime_checkable
class ITool(IComponent, Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        ...

    @property
    def input_schema(self) -> dict[str, Any]:
        ...

    @property
    def output_schema(self) -> dict[str, Any]:
        ...

    @property
    def tool_type(self) -> ToolType:
        ...

    @property
    def risk_level(self):
        ...

    @property
    def requires_approval(self) -> bool:
        ...

    @property
    def timeout_seconds(self) -> int:
        ...

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        ...

    @property
    def is_work_unit(self) -> bool:
        ...

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        ...


class IToolkit(Protocol):
    def register_tool(self, tool: ITool) -> None:
        ...

    def get_tool(self, name: str) -> ITool | None:
        ...

    def list_tools(self) -> list[ToolDefinition]:
        ...


@runtime_checkable
class ISkill(IComponent, Protocol):
    @property
    def name(self) -> str:
        ...

    async def execute(self, input: dict[str, Any], context: RunContext) -> ToolResult:
        ...


class ISkillRegistry(Protocol):
    def register_skill(self, skill: ISkill) -> None:
        ...

    def get_skill(self, name: str) -> ISkill | None:
        ...

    def list_skills(self) -> list[ISkill]:
        ...


class IToolRuntime(Protocol):
    async def invoke(
        self,
        name: str,
        input: dict[str, Any],
        ctx: RunContext,
        envelope: Envelope | None = None,
    ) -> ToolResult:
        ...

    def get_tool(self, name: str) -> ITool | None:
        ...

    def list_tools(self) -> list[ToolDefinition]:
        ...

    def is_plan_tool(self, name: str) -> bool:
        ...


class IPolicyEngine(Protocol):
    def check_tool_access(self, tool: ITool, ctx: RunContext) -> PolicyDecision:
        ...

    def needs_approval(self, milestone: Milestone, validated_plan: ValidatedPlan) -> bool:
        ...

    def enforce(self, action: str, resource: str, ctx: RunContext) -> None:
        ...


class IPlanGenerator(Protocol):
    async def generate_plan(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        plan_attempts: list[dict[str, Any]],
        ctx: RunContext,
    ) -> ProposedPlan:
        ...


@runtime_checkable
class IValidator(IComponent, Protocol):
    async def validate_plan(self, proposed_steps: list[ProposedStep], ctx: RunContext) -> ValidationResult:
        ...

    async def validate_milestone(
        self,
        milestone: Milestone,
        execute_result: "ExecuteResult",
        ctx: RunContext,
    ) -> VerifyResult:
        ...

    async def validate_evidence(self, evidence: list[Evidence], predicate: DonePredicate) -> bool:
        ...


class IRemediator(Protocol):
    async def remediate(
        self,
        verify_result: VerifyResult,
        tool_errors: list["ToolErrorRecord"],
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> str:
        ...


class IContextAssembler(Protocol):
    async def assemble(
        self,
        milestone: Milestone,
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> AssembledContext:
        ...

    async def compress(self, context: AssembledContext, max_tokens: int) -> AssembledContext:
        ...


@runtime_checkable
class IModelAdapter(IComponent, Protocol):
    async def generate(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        ...

    async def generate_structured(self, messages: list[Message], output_schema: type[Any]) -> Any:
        ...


@runtime_checkable
class IMemory(IComponent, Protocol):
    async def store(self, key: str, value: str, metadata: dict | None = None) -> None:
        ...

    async def search(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        ...

    async def get(self, key: str) -> str | None:
        ...


@runtime_checkable
class IHook(IComponent, Protocol):
    async def on_event(self, event: Event) -> None:
        ...


@runtime_checkable
class IMCPClient(IComponent, Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def transport(self) -> str:
        ...

    async def connect(self) -> None:
        ...

    async def disconnect(self) -> None:
        ...

    async def list_tools(self) -> list[ToolDefinition]:
        ...

    async def call_tool(self, tool_name: str, arguments: dict[str, Any], context: RunContext) -> ToolResult:
        ...

    async def list_resources(self) -> list[Resource]:
        ...

    async def read_resource(self, uri: str) -> ResourceContent:
        ...


class IAgent(Protocol, Generic[DepsT, OutputT]):
    async def run(self, task: Task, deps: DepsT) -> RunResult[OutputT]:
        ...


@runtime_checkable
class IConfigProvider(IComponent, Protocol):
    def get(self, key: str, default: Any | None = None) -> Any:
        ...

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        ...


@runtime_checkable
class IPromptStore(IComponent, Protocol):
    def get_prompt(self, name: str, version: str | None = None) -> str:
        ...


from .models import ExecuteResult, ToolErrorRecord
