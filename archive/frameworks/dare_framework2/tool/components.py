"""Tool domain component interfaces."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dare_framework2.tool.types import CapabilityDescriptor, RiskLevel, RunContext, ToolResult, ToolType


# =============================================================================
# Tool Interface
# =============================================================================

@runtime_checkable
class ITool(Protocol):
    """Executable tool contract.
    
    Tools are capability implementations. Side effects must be routed
    through the Kernel IToolGateway boundary, but tool implementations
    are kept as plain Python objects for ease of extension.
    """

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for input validation."""
        ...

    @property
    def output_schema(self) -> dict[str, Any]:
        """JSON Schema for output."""
        ...

    @property
    def tool_type(self) -> ToolType:
        """Tool classification (atomic or work unit)."""
        ...

    @property
    def risk_level(self) -> RiskLevel:
        """Security risk classification."""
        ...

    @property
    def requires_approval(self) -> bool:
        """Whether HITL approval is required."""
        ...

    @property
    def timeout_seconds(self) -> int:
        """Execution timeout in seconds."""
        ...

    @property
    def produces_assertions(self) -> list[dict[str, Any]]:
        """Assertions this tool can produce."""
        ...

    @property
    def is_work_unit(self) -> bool:
        """Whether this is a work unit tool."""
        ...

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Execute the tool.
        
        Args:
            input: Tool input parameters
            context: Execution context
            
        Returns:
            Tool execution result with evidence
        """
        ...


# =============================================================================
# Skill Interface
# =============================================================================

@runtime_checkable
class ISkill(Protocol):
    """A pluggable skill capability.
    
    Skills are similar to tools but may be used for higher-level
    operations or plan-time macros.
    """

    @property
    def name(self) -> str:
        """Unique skill identifier."""
        ...

    async def execute(
        self,
        input: dict[str, Any],
        context: RunContext[Any],
    ) -> ToolResult:
        """Execute the skill.
        
        Args:
            input: Skill input parameters
            context: Execution context
            
        Returns:
            Execution result
        """
        ...


# =============================================================================
# Capability Provider Interface
# =============================================================================

class ICapabilityProvider(Protocol):
    """Provides capabilities to the Kernel tool gateway.
    
    Capability providers abstract the source of capabilities,
    whether they are local tools, MCP servers, or other agents.
    """

    async def list(self) -> list[CapabilityDescriptor]:
        """List all available capabilities.
        
        Returns:
            List of capability descriptors
        """
        ...

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
    ) -> object:
        """Invoke a capability.
        
        Args:
            capability_id: The capability to invoke
            params: Invocation parameters
            
        Returns:
            Capability result
        """
        ...

