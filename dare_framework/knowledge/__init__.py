"""knowledge domain facade."""

from dare_framework.knowledge.interfaces import IKnowledgeTool
from dare_framework.knowledge.kernel import IKnowledge

__all__ = [
    "IKnowledge",
    "IKnowledgeTool",
]
