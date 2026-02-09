"""Model domain component manager interfaces."""

from __future__ import annotations

from abc import ABC
from typing import Protocol

from dare_framework.config.types import Config
from dare_framework.model.kernel import IModelAdapter
from dare_framework.model.types import Prompt

class IModelAdapterManager(ABC):
    """Loads the model adapter implementation (single-select)."""

    def load_model_adapter(self, *, config: Config | None = None) -> IModelAdapter | None: ...

class IPromptLoader(ABC):
    """Loads Prompt definitions from a single source."""

    def load(self) -> list[Prompt]:
        ...


class IPromptStore(ABC):
    """Resolves Prompt definitions by id, model identity, and optional version."""

    def get(self, prompt_id: str, *, model: str | None = None, version: str | None = None) -> Prompt:
        ...


__all__ = ["IModelAdapterManager", "IPromptLoader", "IPromptStore"]
