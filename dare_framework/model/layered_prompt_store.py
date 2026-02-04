"""Layered prompt store implementation."""

from __future__ import annotations

from dataclasses import dataclass

from dare_framework.model.interfaces import IPromptLoader, IPromptStore
from dare_framework.model.types import Prompt


@dataclass(frozen=True)
class _PromptEntry:
    prompt: Prompt
    source_rank: int
    source_index: int


class LayeredPromptStore(IPromptStore):
    """Resolves prompts from multiple loaders with deterministic precedence."""

    def __init__(self, loaders: list[IPromptLoader]) -> None:
        self._loaders = list(loaders)
        self._entries = self._load_entries()

    def get(self, prompt_id: str, *, model: str | None = None, version: str | None = None) -> Prompt:
        candidates = []
        for entry in self._entries:
            prompt = entry.prompt
            if prompt.prompt_id != prompt_id:
                continue
            if version is not None and prompt.version != version:
                continue
            if model is not None and model not in prompt.supported_models and "*" not in prompt.supported_models:
                continue
            candidates.append(entry)
        if not candidates:
            raise KeyError(f"Prompt not found: {prompt_id}")
        selected = sorted(
            candidates,
            key=lambda item: (-item.prompt.order, item.source_rank, item.source_index),
        )[0]
        return selected.prompt

    def _load_entries(self) -> list[_PromptEntry]:
        entries: list[_PromptEntry] = []
        for source_rank, loader in enumerate(self._loaders):
            prompts = loader.load()
            for source_index, prompt in enumerate(prompts):
                entries.append(_PromptEntry(prompt=prompt, source_rank=source_rank, source_index=source_index))
        return entries


__all__ = ["LayeredPromptStore"]