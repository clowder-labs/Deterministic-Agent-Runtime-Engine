"""Built-in prompt loader."""

from __future__ import annotations

from dare_framework.model.types import Prompt


def _default_prompts() -> list[Prompt]:
    return [
        Prompt(
            prompt_id="base.system",
            role="system",
            content="You are a deterministic agent runtime.",
            supported_models=["*"],
            order=0,
        )
    ]


class BuiltInPromptLoader:
    """Loads built-in prompts shipped with the framework."""

    def __init__(self, prompts: list[Prompt] | None = None) -> None:
        self._prompts = list(prompts) if prompts is not None else _default_prompts()

    def load(self) -> list[Prompt]:
        return list(self._prompts)


__all__ = ["BuiltInPromptLoader"]
