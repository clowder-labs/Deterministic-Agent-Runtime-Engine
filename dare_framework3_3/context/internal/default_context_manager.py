"""Default context manager implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dare_framework3_3.context.kernel import IContextManager
from dare_framework3_3.context.types import (
    AssembledContext,
    AssemblyRequest,
    ContextPacket,
    ContextStage,
    IndexStatus,
    RetrievedContext,
    RuntimeStateView,
    SessionContext,
    Message,
)

if TYPE_CHECKING:
    from dare_framework3_3.config.kernel import IConfigProvider
    from dare_framework3_3.config.types import Config
    from dare_framework3_3.memory.component import IMemory
    from dare_framework3_3.plan.types import Task
    from dare_framework3_3.context.types import Budget
    from dare_framework3_3.tool.kernel import IToolGateway


class _DefaultAssemblyContext:
    """Default session-scoped assembly context.

    This object is held by SessionContext and is responsible for producing the
    final message list that can be sent directly to an LLM.
    """

    def __init__(
        self,
        *,
        user_input: str,
        config: "Config | None" = None,
        tool_gateway: "IToolGateway | None" = None,
    ) -> None:
        self._user_input = user_input
        # Session-scoped config snapshot. Do not read from ConfigProvider on each assemble()
        # call to avoid surprising mid-session behavior after a reload.
        self._config = config
        self._tool_gateway = tool_gateway

    async def _tool_catalog_message(self) -> Message | None:
        """Build a deterministic tool catalog as a system message.

        Tools are injected into the model's context as messages (Context Engineering Layer 3).
        Model adapters that support function calling may still consume structured tool
        definitions separately; this catalog is for LLM reasoning and auditability.
        """
        if self._tool_gateway is None:
            return None

        from dare_framework3_3.tool.types import CapabilityType

        config = self._config
        allowtools = set(config.allowtools) if config is not None and config.allowtools else set()
        capabilities = await self._tool_gateway.list_capabilities()
        tools = [
            cap
            for cap in capabilities
            if cap.type == CapabilityType.TOOL
            and (
                not allowtools
                or cap.name in allowtools
                or cap.id in allowtools
            )
        ]
        tools.sort(key=lambda cap: cap.id)

        if not tools:
            return None

        lines = ["Tool catalog (capability_id -> description):"]
        for cap in tools:
            meta = cap.metadata or {}
            suffix_parts: list[str] = []
            risk_level = meta.get("risk_level")
            if isinstance(risk_level, str) and risk_level:
                suffix_parts.append(f"risk={risk_level}")
            requires_approval = meta.get("requires_approval")
            if isinstance(requires_approval, bool):
                suffix_parts.append(f"approval={requires_approval}")
            timeout_seconds = meta.get("timeout_seconds")
            if isinstance(timeout_seconds, (int, float)):
                suffix_parts.append(f"timeout={int(timeout_seconds)}s")
            suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
            lines.append(f"- {cap.id}: {cap.description}{suffix}")

        return Message(
            role="system",
            content="\n".join(lines),
            metadata={"type": "tool_catalog"},
        )

    async def assemble(self, req: AssemblyRequest) -> list[Message]:
        """Assemble a message list for the request stage."""
        user_content = (
            req.state.data.get("user_input")
            or req.state.data.get("task_description")
            or self._user_input
            or ""
        )

        messages: list[Message] = [
            Message(role="system", content=f"DARE Kernel v3.0 stage={req.stage.value}"),
        ]
        tool_catalog = await self._tool_catalog_message()
        if tool_catalog is not None:
            messages.append(tool_catalog)
        messages.append(Message(role="user", content=str(user_content)))
        return messages


class DefaultContextManager(IContextManager):
    """Minimal context manager supporting PLAN/EXECUTE assembly.
    
    This is an MVP implementation that provides basic context assembly
    for the plan and execute stages. More sophisticated context engineering
    can be added in future implementations.
    
    Args:
        memory: Optional memory component for retrieval operations
    """

    def __init__(
        self,
        *,
        memory: "IMemory | None" = None,
        config_provider: "IConfigProvider | None" = None,
        tool_gateway: "IToolGateway | None" = None,
    ) -> None:
        self._memory = memory
        # Config is provided by the config domain; do not pass it through retrieval/assembly requests.
        self._config_provider = config_provider
        self._tool_gateway = tool_gateway
        self._active_session: SessionContext | None = None
        self._active_task_id: str | None = None

    def _safe_config_summary(self, *, config: "Config | None") -> dict[str, Any] | None:
        """Return a sanitized config snapshot suitable for metadata/debugging."""
        if config is None:
            return None
        # Avoid leaking secrets (e.g., API keys). Only include safe, high-level fields.
        return {
            "llm": {
                "adapter": config.llm.adapter,
                "endpoint": config.llm.endpoint,
                "model": config.llm.model,
            },
            "allowtools": list(config.allowtools),
            "allowmcps": list(config.allowmcps),
            "workspace_roots": list(config.workspace_roots),
        }

    def open_session(self, task: "Task") -> SessionContext:
        """Open a session for the given task."""
        config = self._config_provider.current() if self._config_provider is not None else None
        session = SessionContext(
            user_input=task.description,
            metadata={"task_id": task.task_id},
            config=config,
            assembly=_DefaultAssemblyContext(
                user_input=task.description,
                config=config,
                tool_gateway=self._tool_gateway,
            ),
        )
        self._active_session = session
        self._active_task_id = task.task_id
        return session

    async def assemble(
        self,
        stage: ContextStage,
        state: RuntimeStateView,
    ) -> AssembledContext:
        """Assemble context for the given stage.

        This remains as a Kernel-level convenience wrapper. Preferred usage is to call:
        `session = open_session(task)` and then `await session.assembly.assemble(...)`.
        """
        session = (
            self._active_session
            if self._active_session is not None and self._active_task_id == state.task_id
            else None
        )
        if session is None:
            config = self._config_provider.current() if self._config_provider is not None else None
            session = SessionContext(
                user_input=str(state.data.get("task_description") or ""),
                metadata={"task_id": state.task_id},
                config=config,
                assembly=_DefaultAssemblyContext(
                    user_input=str(state.data.get("task_description") or ""),
                    config=config,
                    tool_gateway=self._tool_gateway,
                ),
            )

        if session.assembly is None:
            raise RuntimeError("SessionContext.assembly is not set")

        messages = await session.assembly.assemble(AssemblyRequest(stage=stage, state=state))
        metadata: dict[str, Any] = {
            **session.metadata,
            "task_id": state.task_id,
            "run_id": state.run_id,
            "milestone_id": state.milestone_id,
            "stage": stage.value,
        }
        config_summary = self._safe_config_summary(config=session.config)
        if config_summary is not None:
            metadata["config"] = config_summary
        return AssembledContext(messages=messages, metadata=metadata)

    async def retrieve(
        self,
        query: str,
        *,
        budget: "Budget",
    ) -> RetrievedContext:
        """Retrieve context from memory if available."""
        if self._memory is None:
            return RetrievedContext(items=[])
        items = await self._memory.retrieve(query, budget=budget)
        return RetrievedContext(items=list(items))

    async def ensure_index(self, scope: str) -> IndexStatus:
        """MVP: Always report index as ready."""
        return IndexStatus(ready=True, details={"scope": scope, "mode": "noop"})

    async def compress(
        self,
        context: AssembledContext,
        *,
        budget: "Budget",
    ) -> AssembledContext:
        """MVP: Return context unchanged (no compression)."""
        return context

    async def route(self, packet: ContextPacket, target: str) -> None:
        """MVP: No-op routing."""
        pass
