"""knowledge domain pluggable interfaces (composed capabilities).

Alignment note:
When a domain needs both retrieval and callable capability semantics, provide a
composed interface in `interfaces.py`.
"""

from __future__ import annotations

from abc import ABC

from dare_framework.knowledge.kernel import IKnowledge
from dare_framework.tool.kernel import ITool


class IKnowledgeTool(IKnowledge, ITool, ABC):
    """A knowledge retriever that is also exposed as a tool capability."""


__all__ = ["IKnowledgeTool"]
