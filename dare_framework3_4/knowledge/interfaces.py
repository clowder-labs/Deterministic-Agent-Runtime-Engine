"""knowledge domain pluggable interfaces (composed capabilities).

v4.0 alignment note:
When a domain needs both retrieval and callable capability semantics, provide a
composed interface in `interfaces.py`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dare_framework3_4.knowledge.kernel import IKnowledge
from dare_framework3_4.tool.interfaces import ITool


@runtime_checkable
class IKnowledgeTool(IKnowledge, ITool, Protocol):
    """A knowledge retriever that is also exposed as a tool capability."""


__all__ = ["IKnowledgeTool"]
