"""Default ToolGateway implementation.

Aggregates multiple capability providers into a single invocation surface.
Implements the system-call boundary for all external side-effects (V4 invariant).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Any, Sequence

from dare_framework.tool.kernel import IToolGateway
from dare_framework.tool.types import (
    CapabilityDescriptor,
    InvocationContext,
    ProviderStatus,
)

if TYPE_CHECKING:
    from dare_framework.plan.types import Envelope
    from dare_framework.tool.interfaces import ICapabilityProvider


class DefaultToolGateway(IToolGateway):
    """Aggregates multiple capability providers into a single invocation surface.
    
    V4 alignment:
    - All side-effects MUST flow through invoke()
    - Enforces envelope allow-lists
    - Routes invocations to the appropriate provider
    - Supports execution policies (timeout, retry)
    - Maintains capability cache for performance
    """

    def __init__(
        self,
        *,
        default_timeout: float = 30.0,
        max_retries: int = 0,
        cache_ttl: float = 60.0,
    ) -> None:
        """Initialize the gateway.
        
        Args:
            default_timeout: Default timeout for invocations in seconds.
            max_retries: Maximum retry attempts for failed invocations.
            cache_ttl: Time-to-live for capability cache in seconds.
        """
        self._providers: list[ICapabilityProvider] = []
        self._capability_to_provider: dict[str, ICapabilityProvider] = {}
        self._capability_cache: list[CapabilityDescriptor] = []
        self._cache_timestamp: float = 0.0
        self._default_timeout = default_timeout
        self._max_retries = max_retries
        self._cache_ttl = cache_ttl

    def register_provider(self, provider: object) -> None:
        """Register a capability provider.
        
        Args:
            provider: Must implement ICapabilityProvider protocol.
        """
        from dare_framework.tool.interfaces import ICapabilityProvider
        if not isinstance(provider, ICapabilityProvider):
            raise TypeError(f"Provider must implement ICapabilityProvider, got {type(provider)}")
        self._providers.append(provider)
        # Invalidate cache when new provider is registered
        self._cache_timestamp = 0.0

    def unregister_provider(self, provider: object) -> bool:
        """Unregister a capability provider.
        
        Args:
            provider: The provider to remove.
            
        Returns:
            True if provider was found and removed, False otherwise.
        """
        try:
            self._providers.remove(provider)  # type: ignore
            self._cache_timestamp = 0.0
            return True
        except ValueError:
            return False

    async def list_capabilities(self) -> Sequence[CapabilityDescriptor]:
        """List all capabilities from all providers.
        
        Uses caching to avoid repeated discovery calls.
        """
        now = time.time()
        if self._cache_timestamp > 0 and (now - self._cache_timestamp) < self._cache_ttl:
            return self._capability_cache

        capabilities: list[CapabilityDescriptor] = []
        mapping: dict[str, ICapabilityProvider] = {}
        
        for provider in self._providers:
            try:
                for capability in await provider.list():
                    if capability.id in mapping:
                        raise ValueError(f"Duplicate capability id: {capability.id}")
                    mapping[capability.id] = provider
                    capabilities.append(capability)
            except Exception as e:
                # Re-raise configuration errors like duplicate IDs
                if isinstance(e, ValueError):
                    raise
                # Log but continue with other providers
                # In production, this would use proper logging
                pass
        
        self._capability_to_provider = mapping
        self._capability_cache = capabilities
        self._cache_timestamp = now
        return capabilities

    async def invoke(
        self,
        capability_id: str,
        params: dict[str, Any],
        *,
        envelope: "Envelope",
    ) -> Any:
        """Invoke a capability within an envelope.
        
        Args:
            capability_id: The capability to invoke.
            params: Parameters to pass to the capability.
            envelope: Execution boundary (allow-list, budget, done predicate).
            
        Returns:
            The result from the capability invocation.
            
        Raises:
            PermissionError: If capability is not in envelope allow-list.
            KeyError: If capability_id is not found.
            TimeoutError: If invocation exceeds timeout.
        """
        # Check envelope allow-list
        if envelope.allowed_capability_ids and capability_id not in envelope.allowed_capability_ids:
            raise PermissionError(f"Capability '{capability_id}' not allowed by envelope")

        # Find the provider
        provider = self._capability_to_provider.get(capability_id)
        if provider is None:
            # Refresh cache for dynamic providers
            await self.list_capabilities()
            provider = self._capability_to_provider.get(capability_id)
        
        if provider is None:
            raise KeyError(f"Unknown capability id: {capability_id}")

        # Create invocation context for tracing
        invocation_ctx = InvocationContext(
            invocation_id=str(uuid.uuid4()),
            capability_id=capability_id,
        )

        # Execute with timeout and retry policy
        timeout = self._default_timeout
        last_error: Exception | None = None
        
        for attempt in range(self._max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    provider.invoke(capability_id, params),
                    timeout=timeout,
                )
                return result
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Invocation of '{capability_id}' timed out after {timeout}s")
                if attempt < self._max_retries:
                    continue
            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    continue
                
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected invocation failure")

    async def health_check(self) -> dict[str, ProviderStatus]:
        """Check health of all registered providers.
        
        Returns:
            Mapping of provider index to health status.
        """
        results: dict[str, ProviderStatus] = {}
        for i, provider in enumerate(self._providers):
            try:
                status = await provider.health_check()
                results[f"provider_{i}"] = status
            except Exception:
                results[f"provider_{i}"] = ProviderStatus.UNKNOWN
        return results

    def invalidate_cache(self) -> None:
        """Force cache invalidation."""
        self._cache_timestamp = 0.0


__all__ = ["DefaultToolGateway"]
