"""knowledge domain facade."""

from dare_framework3_4.knowledge.interfaces import IKnowledgeTool
from dare_framework3_4.knowledge.kernel import IKnowledge

__all__ = [
    "IKnowledge",
    "IKnowledgeTool",
]
