"""Security domain interfaces.

This module contains the ISecurityBoundary interface, which is a Layer 0 Kernel
interface responsible for:
- Trust verification: Deriving trusted input from untrusted parameters
- Policy checking: Determining allow/deny/require-approval decisions
- Safe execution: Running functions in sandboxed environments
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from dare_framework3.tool.types import TrustedInput, PolicyDecision, SandboxSpec


# =============================================================================
# Security Boundary Interface (Layer 0 Kernel)
# =============================================================================

class ISecurityBoundary(Protocol):
    """Trust + Policy + Sandbox boundary.
    
    The security boundary handles:
    - Trust verification (deriving trusted fields from registries)
    - Policy checking (allow/deny/require-approval)
    - Safe execution (sandbox isolation)
    
    This is a Layer 0 Kernel interface.
    """

    async def verify_trust(
        self,
        *,
        input: dict[str, Any],
        context: dict[str, Any],
    ) -> TrustedInput:
        """Derive trusted input from untrusted parameters.
        
        Args:
            input: Untrusted input parameters
            context: Security context (registry info, etc.)
            
        Returns:
            Trusted input with derived security fields
        """
        ...

    async def check_policy(
        self,
        *,
        action: str,
        resource: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        """Check policy for an action.
        
        Args:
            action: The action being performed
            resource: The resource being accessed
            context: Security context
            
        Returns:
            Policy decision (allow/deny/require-approval)
        """
        ...

    async def execute_safe(
        self,
        *,
        action: str,
        fn: Callable[[], Any],
        sandbox: SandboxSpec,
    ) -> Any:
        """Execute a function in a sandbox.
        
        Args:
            action: Description of the action
            fn: The function to execute
            sandbox: Sandbox configuration
            
        Returns:
            Function result
        """
        ...
