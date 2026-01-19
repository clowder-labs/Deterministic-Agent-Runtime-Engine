"""No-op prompt store implementation."""

from __future__ import annotations

from dare_framework2.memory.interfaces import IPromptStore


class NoOpPromptStore(IPromptStore):
    """A prompt store that returns no templates.
    
    Useful as a default when no prompt store is configured,
    or for testing scenarios.
    """

    async def get(self, prompt_id: str) -> str | None:
        """Always returns None - no prompts stored."""
        return None

    async def set(self, prompt_id: str, content: str) -> None:
        """Does nothing - prompts are discarded."""
        pass
