from __future__ import annotations

from enum import Enum
from typing import Any, AsyncIterator, Generic, Protocol, TypeVar

from dare_framework.core.events import Event, EventFilter, EventID
from dare_framework.core.models import (
    AssembledContext,
    DonePredicate,
    Envelope,
    Evidence,
    ExecuteResult,
    GenerateOptions,
    MemoryItem,
    Message,
    Milestone,
    MilestoneContext,
    ModelResponse,
    MilestoneSummary,
    ProposedPlan,
    ProposedStep,
    RunContext,
    RunResult,
    SessionSummary,
    Task,
    ToolDefinition,
    ToolResult,
    ToolError,
    ValidationResult,
    ValidatedPlan,
    VerifyResult,
)
from dare_framework.core.models import RiskLevel, ToolType
from dare_framework.core.state import RuntimeState

DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")
T = TypeVar("T")


class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVE_REQUIRED = "approve_required"


class IEventLog(Protocol):
    async def append(self, event: Event) -> EventID:
        ...

    async def query(
        self,
        filter: EventFilter | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Event]:
        ...

    async def verify_chain(self) -> bool:
        ...

    async def get_checkpoint_events(self, checkpoint_id: str) -> list[Event]:
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


class IValidator(Protocol):
    async def validate_plan(
        self,
        proposed_steps: list[ProposedStep],
        ctx: RunContext,
    ) -> ValidationResult:
        ...

    async def validate_milestone(
        self,
        milestone: Milestone,
        execute_result: ExecuteResult,
        ctx: RunContext,
    ) -> VerifyResult:
        ...

    async def validate_evidence(self, evidence: list[Evidence], predicate: DonePredicate) -> bool:
        ...


class IRemediator(Protocol):
    async def remediate(
        self,
        verify_result: VerifyResult,
        tool_errors: list[ToolError],
        milestone_ctx: MilestoneContext,
        ctx: RunContext,
    ) -> str:
        ...


class ISkillRegistry(Protocol):
    def register_skill(self, skill: ISkill) -> None:
        ...

    def get_skill(self, name: str) -> ISkill | None:
        ...

    def list_skills(self) -> list[ISkill]:
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


class IModelAdapter(Protocol):
    async def generate(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        options: GenerateOptions | None = None,
    ) -> ModelResponse:
        ...

    async def generate_structured(
        self,
        messages: list[Message],
        output_schema: type[Any],
    ) -> Any:
        ...


class IMemory(Protocol):
    async def store(self, key: str, value: str, metadata: dict | None = None) -> None:
        ...

    async def search(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        ...

    async def get(self, key: str) -> str | None:
        ...


class ITool(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        ...

    @property
    def tool_type(self) -> ToolType:
        ...

    @property
    def risk_level(self) -> RiskLevel:
        ...

    def get_input_schema(self) -> dict[str, Any]:
        ...

    async def execute(self, input: dict[str, Any], ctx: RunContext) -> ToolResult:
        ...


class ISkill(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        ...

    def get_envelope(self, input: dict[str, Any]) -> Envelope:
        ...

    def get_done_predicate(self, input: dict[str, Any]) -> DonePredicate:
        ...

    def get_input_schema(self) -> dict[str, Any]:
        ...


class IToolkit(Protocol):
    def register_tool(self, tool: ITool) -> None:
        ...

    def get_tool(self, name: str) -> ITool | None:
        ...

    def list_tools(self) -> list[ITool]:
        ...

    def activate_group(self, group_name: str) -> None:
        ...


class IMCPClient(Protocol):
    async def connect(self, server_config: dict[str, Any]) -> None:
        ...

    async def list_tools(self) -> list[dict[str, Any]]:
        ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        ...

    async def disconnect(self) -> None:
        ...


class IHook(Protocol):
    async def on_session_start(self, task: Task) -> None:
        ...

    async def on_milestone_start(self, milestone: Milestone) -> None:
        ...

    async def on_tool_call(self, tool_name: str, input: dict[str, Any], result: ToolResult) -> None:
        ...

    async def on_session_end(self, result: RunResult[Any]) -> None:
        ...


class ICheckpoint(Protocol):
    async def save(self, task_id: str, state: RuntimeState, milestone_id: str | None = None) -> str:
        ...

    async def load(self, checkpoint_id: str) -> RuntimeState:
        ...

    async def save_milestone_summary(
        self,
        milestone_id: str,
        summary: MilestoneSummary,
    ) -> None:
        ...

    async def load_milestone_summary(self, milestone_id: str) -> MilestoneSummary:
        ...

    async def is_completed(self, milestone_id: str) -> bool:
        ...

    async def save_session_summary(self, summary: SessionSummary) -> None:
        ...

    async def load_session_summary(self, session_id: str) -> SessionSummary | None:
        ...


class IStreamedResponse(Protocol, Generic[T]):
    async def __aiter__(self) -> AsyncIterator[T]:
        ...
