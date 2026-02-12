"""Public factory functions for model-domain defaults."""

from __future__ import annotations

from pathlib import Path

from dare_framework.config.types import Config
from dare_framework.model.interfaces import IPromptStore
from dare_framework.model.builtin_prompt_loader import BuiltInPromptLoader
from dare_framework.model.filesystem_prompt_loader import FileSystemPromptLoader
from dare_framework.model.layered_prompt_store import LayeredPromptStore


def create_default_prompt_store(config: Config) -> IPromptStore:
    """Create the default prompt store using layered prompt manifests."""
    if config is None:
        raise ValueError("create_default_prompt_store requires a non-null Config.")
    effective = config
    pattern = effective.prompt_store_path_pattern
    workspace_manifest = Path(effective.workspace_dir) / pattern
    user_manifest = Path(effective.user_dir) / pattern
    loaders = [
        FileSystemPromptLoader(workspace_manifest),
        FileSystemPromptLoader(user_manifest),
        BuiltInPromptLoader(),
    ]
    return LayeredPromptStore(loaders)


__all__ = ["create_default_prompt_store"]
