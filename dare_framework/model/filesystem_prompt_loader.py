"""Filesystem prompt loader for manifest files."""

from __future__ import annotations

import json
from pathlib import Path

from dare_framework.model import IPromptLoader
from dare_framework.model.types import Prompt


class FileSystemPromptLoader(IPromptLoader):
    """Loads prompt manifests from a JSON file path."""

    def __init__(self, manifest_path: str | Path) -> None:
        self._manifest_path = Path(manifest_path)

    def load(self) -> list[Prompt]:
        if not self._manifest_path.exists():
            return []
        if not self._manifest_path.is_file():
            return []
        try:
            payload = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        prompts_raw = payload.get("prompts") if isinstance(payload, dict) else None
        if not isinstance(prompts_raw, list):
            return []
        prompts: list[Prompt] = []
        for item in prompts_raw:
            if not isinstance(item, dict):
                continue
            prompt = Prompt.from_dict(item)
            if not _is_valid_prompt(prompt):
                continue
            prompts.append(prompt)
        return prompts


def _is_valid_prompt(prompt: Prompt) -> bool:
    if not prompt.prompt_id:
        return False
    if not prompt.role:
        return False
    if prompt.content == "":
        return False
    if not prompt.supported_models:
        return False
    return True


__all__ = ["FileSystemPromptLoader"]
