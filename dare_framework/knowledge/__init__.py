"""knowledge domain facade."""

from dare_framework.knowledge.interfaces import IKnowledgeTool
from dare_framework.knowledge.kernel import IKnowledge
from dare_framework.knowledge.factory import create_knowledge
from dare_framework.knowledge.types import KnowledgeConfig

__all__ = [
    "IKnowledge",
    "IKnowledgeTool",
    "KnowledgeConfig",
    "create_knowledge",
]
