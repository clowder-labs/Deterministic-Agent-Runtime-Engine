"""knowledge domain facade."""

from dare_framework.knowledge.interfaces import IKnowledgeTool
from dare_framework.knowledge.kernel import IKnowledge
from dare_framework.knowledge._internal.vector_knowledge import Document, VectorKnowledge

__all__ = [
    "IKnowledge",
    "IKnowledgeTool",
    "Document",
    "VectorKnowledge",
]
