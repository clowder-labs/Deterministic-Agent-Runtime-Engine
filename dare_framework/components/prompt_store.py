from __future__ import annotations

from ..core.interfaces import IPromptStore
from .base_component import BaseComponent


class InMemoryPromptStore(BaseComponent, IPromptStore):
    def __init__(self, prompts: dict[tuple[str, str | None], str] | None = None) -> None:
        self._prompts = prompts or {}

    def get_prompt(self, name: str, version: str | None = None) -> str:
        key = (name, version)
        if key in self._prompts:
            return self._prompts[key]
        fallback = (name, None)
        if fallback in self._prompts:
            return self._prompts[fallback]
        raise KeyError(f"Prompt not found: {name} ({version})")
