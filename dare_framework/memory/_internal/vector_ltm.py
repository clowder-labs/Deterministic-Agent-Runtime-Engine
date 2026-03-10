"""Long-term memory implementation backed by vector store (embedding + similarity search)."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Literal

from dare_framework.context import AttachmentRef, Message, MessageKind, MessageMark, MessageRole
from dare_framework.embedding import IEmbeddingAdapter
from dare_framework.infra.component import ComponentType, IComponent
from dare_framework.memory.kernel import ILongTermMemory
from dare_framework.knowledge._internal.vector_knowledge.document import Document
from dare_framework.knowledge._internal.vector_knowledge.vector_store.interfaces import (
    IVectorStore,
)


def _message_to_document(message: Message) -> Document:
    """Serialize Message to Document for vector store.

    Vector stores need a concrete text field for embedding. Canonical rich-message
    structure is persisted in document metadata so retrieval can reconstruct the
    original framework message faithfully.
    """
    content = message.text if message.text else " "
    metadata: dict[str, Any] = {
        "role": message.role.value,
        "kind": message.kind.value,
        "text": message.text,
        "attachments": [
            {
                "kind": attachment.kind.value,
                "uri": attachment.uri,
                "mime_type": attachment.mime_type,
                "filename": attachment.filename,
                "metadata": dict(attachment.metadata),
            }
            for attachment in message.attachments
        ],
        "data": dict(message.data or {}),
        "name": message.name,
        "mark": message.mark.value,
        "id": message.id,
        **message.metadata,
    }
    return Document(content=content, metadata=metadata)


def _document_to_message(doc: Document) -> Message:
    """Deserialize Document to Message (restore role/name from metadata)."""
    meta = doc.metadata or {}
    attachments_raw = meta.get("attachments")
    data_raw = meta.get("data")
    return Message(
        role=meta.get("role", MessageRole.USER),
        kind=meta.get("kind", MessageKind.CHAT),
        text=meta.get("text", doc.content),
        attachments=AttachmentRef.coerce_many(attachments_raw if isinstance(attachments_raw, list) else []),
        data=dict(data_raw) if isinstance(data_raw, dict) else None,
        name=meta.get("name"),
        metadata={
            k: v
            for k, v in meta.items()
            if k not in ("role", "kind", "text", "attachments", "data", "name", "mark", "id")
        },
        mark=meta.get("mark", MessageMark.TEMPORARY),
        id=meta.get("id"),
    )


def _run_async(coro):
    """Run async coroutine from sync context (same pattern as VectorKnowledge)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class VectorLongTermMemory(ILongTermMemory, IComponent):
    """Long-term memory backed by vector store (embedding + similarity search).

    Persists Message as Document (content + metadata); get() embeds query and
    returns similar documents as Messages.
    """

    def __init__(
        self,
        embedding_adapter: IEmbeddingAdapter,
        vector_store: IVectorStore,
        name: str = "vector_ltm",
    ) -> None:
        self._embedding_adapter = embedding_adapter
        self._vector_store = vector_store
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def component_type(self) -> Literal[ComponentType.MEMORY]:
        return ComponentType.MEMORY

    def get(self, query: str = "", **kwargs: Any) -> list[Message]:
        top_k = kwargs.get("top_k", 10)
        if not isinstance(top_k, int):
            top_k = 10
        min_similarity = kwargs.get("min_similarity")
        query_vector = _run_async(self._embedding_adapter.embed(query)).vector
        results = self._vector_store.search(
            query_embedding=query_vector,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        messages: list[Message] = []
        for doc, similarity in results:
            msg = _document_to_message(doc)
            msg.metadata["similarity"] = similarity
            messages.append(msg)
        return messages

    async def persist(self, messages: list[Message]) -> None:
        if not messages:
            return
        documents: list[Document] = [_message_to_document(m) for m in messages]
        texts = [d.content for d in documents]
        results = await self._embedding_adapter.embed_batch(texts)
        for doc, emb_result in zip(documents, results):
            doc.embedding = emb_result.vector
        self._vector_store.add_batch(documents)


__all__ = ["VectorLongTermMemory"]
