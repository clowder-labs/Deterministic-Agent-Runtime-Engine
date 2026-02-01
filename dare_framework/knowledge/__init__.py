"""knowledge domain facade."""

from dare_framework.knowledge.interfaces import IKnowledgeTool
from dare_framework.knowledge.kernel import IKnowledge
from dare_framework.knowledge._internal.vector_knowledge import Document, VectorKnowledge
from dare_framework.knowledge._internal.rawdata_knowledge import RawDataKnowledge
from dare_framework.knowledge._internal.rawdata_knowledge.storage import (
    InMemoryRawDataStorage,
)
from dare_framework.knowledge._internal.knowledge_tools import (
    KnowledgeAddTool,
    KnowledgeGetTool,
)
from dare_framework.knowledge.factory import create_knowledge
from dare_framework.knowledge.types import KnowledgeConfig

__all__ = [
    "IKnowledge",
    "IKnowledgeTool",
    "Document",
    "VectorKnowledge",
    "RawDataKnowledge",
    "InMemoryRawDataStorage",
    "KnowledgeConfig",
    "create_knowledge",
    "KnowledgeGetTool",
    "KnowledgeAddTool",
]
