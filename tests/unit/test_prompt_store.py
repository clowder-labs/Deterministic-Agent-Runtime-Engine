from __future__ import annotations

from dare_framework.model import Prompt
from dare_framework.model import LayeredPromptStore


class StaticPromptLoader:
    """Simple loader for deterministic prompt store tests."""

    def __init__(self, prompts: list[Prompt]) -> None:
        self._prompts = list(prompts)

    def load(self) -> list[Prompt]:
        return list(self._prompts)


def test_prompt_store_prefers_highest_order_for_model() -> None:
    prompts = [
        Prompt(
            prompt_id="base.system",
            role="system",
            content="low",
            supported_models=["openai"],
            order=1,
        ),
        Prompt(
            prompt_id="base.system",
            role="system",
            content="high",
            supported_models=["openai"],
            order=10,
        ),
    ]
    store = LayeredPromptStore([StaticPromptLoader(prompts)])

    selected = store.get("base.system", model="openai")

    assert selected.content == "high"


def test_prompt_store_falls_back_to_wildcard() -> None:
    prompts = [
        Prompt(
            prompt_id="base.system",
            role="system",
            content="wildcard",
            supported_models=["*"],
            order=0,
        ),
        Prompt(
            prompt_id="base.system",
            role="system",
            content="other",
            supported_models=["anthropic"],
            order=5,
        ),
    ]
    store = LayeredPromptStore([StaticPromptLoader(prompts)])

    selected = store.get("base.system", model="openai")

    assert selected.content == "wildcard"


def test_prompt_store_tiebreaks_by_source_and_order() -> None:
    workspace_prompts = [
        Prompt(
            prompt_id="base.system",
            role="system",
            content="workspace-first",
            supported_models=["openai"],
            order=5,
        ),
        Prompt(
            prompt_id="base.system",
            role="system",
            content="workspace-second",
            supported_models=["openai"],
            order=5,
        ),
    ]
    user_prompts = [
        Prompt(
            prompt_id="base.system",
            role="system",
            content="user",
            supported_models=["openai"],
            order=5,
        )
    ]
    builtin_prompts = [
        Prompt(
            prompt_id="base.system",
            role="system",
            content="builtin",
            supported_models=["openai"],
            order=5,
        )
    ]

    # Loader order matches precedence: workspace > user > built-in.
    store = LayeredPromptStore(
        [
            StaticPromptLoader(workspace_prompts),
            StaticPromptLoader(user_prompts),
            StaticPromptLoader(builtin_prompts),
        ]
    )

    selected = store.get("base.system", model="openai")

    assert selected.content == "workspace-first"
