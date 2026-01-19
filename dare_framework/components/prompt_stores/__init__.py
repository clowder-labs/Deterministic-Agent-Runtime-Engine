"""Prompt store components (Layer 2).

Prompt stores are optional in early v2 milestones. They provide a place to manage
prompt templates/snippets independently from the Kernel so developers can swap
prompt sources without changing core loop code.
"""

from dare_framework.components.prompt_stores.noop import NoOpPromptStore
from dare_framework.components.prompt_stores.protocols import IPromptStore

__all__ = [
    "IPromptStore",
    "NoOpPromptStore",
]

