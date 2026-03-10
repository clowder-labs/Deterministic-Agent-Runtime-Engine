"""Document data format for vector knowledge storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class Document:
    """Document representation for vector knowledge storage.

    A document contains text content, optional metadata, and an embedding vector.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique document identifier."""

    content: str = ""
    """Text content of the document."""

    embedding: list[float] | None = None
    """Embedding vector for semantic search (None if not yet embedded)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Optional metadata (e.g., source, title, timestamp)."""

    def __post_init__(self) -> None:
        """Validate document after initialization."""
        if not self.content:
            raise ValueError("Document content cannot be empty")

    def to_message(self, role: str = "assistant") -> Message:
        """Convert document to Message format for context assembly.

        Args:
            role: Message role (default: "assistant").

        Returns:
            Message object with document content and metadata.
        """
        from dare_framework.context import Message

        return Message(
            role=role,
            text=self.content,
            name=self.metadata.get("source") or self.id,
            metadata={
                **self.metadata,
                "document_id": self.id,
            },
        )


__all__ = ["Document"]
