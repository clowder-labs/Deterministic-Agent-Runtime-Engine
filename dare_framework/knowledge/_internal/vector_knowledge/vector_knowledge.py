"""Vector knowledge retrieval implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dare_framework.embedding import IEmbeddingAdapter
from dare_framework.knowledge.kernel import IKnowledge
from dare_framework.knowledge._internal.vector_knowledge.document import Document
from dare_framework.knowledge._internal.vector_knowledge.vector_store.interfaces import (
    IVectorStore,
)
from dare_framework.knowledge._internal.vector_knowledge.vector_store.in_memory_store import (
    InMemoryVectorStore,
)

if TYPE_CHECKING:
    from dare_framework.context import Message


class VectorKnowledge(IKnowledge):
    """Vector-based knowledge retrieval implementation.

    Uses embedding models to convert queries and documents into vectors,
    then performs similarity search to retrieve relevant knowledge.

    Example:
        embedding_adapter = OpenAIEmbeddingAdapter(model="text-embedding-3-small")
        knowledge = VectorKnowledge(embedding_adapter=embedding_adapter)
        
        # Add documents
        doc = Document(content="Python is a programming language")
        knowledge.add_document(doc)
        
        # Retrieve knowledge
        results = knowledge.get("What is Python?", top_k=3)
    """

    def __init__(
        self,
        embedding_adapter: IEmbeddingAdapter,
        vector_store: IVectorStore | None = None,
    ) -> None:
        """Initialize vector knowledge retrieval.

        Args:
            embedding_adapter: Embedding adapter for generating vectors.
            vector_store: Vector store implementing IVectorStore (e.g. InMemoryVectorStore,
                ChromaDBVectorStore, or custom). Creates a new InMemoryVectorStore if None.
        """
        self._embedding_adapter = embedding_adapter
        self._vector_store = vector_store or InMemoryVectorStore()

    def add(self, content: str, **kwargs: object) -> None:
        """Add content to the knowledge base (IKnowledge.add).

        Wraps content in a Document and delegates to add_document.
        **kwargs: metadata (dict), auto_embed (bool, default True).
        """
        metadata = kwargs.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        auto_embed = kwargs.get("auto_embed", True)
        if not isinstance(auto_embed, bool):
            auto_embed = True
        doc = Document(content=content, metadata=metadata)
        self.add_document(doc, auto_embed=auto_embed)

    def get(self, query: str, **kwargs) -> list[Message]:
        """Retrieve relevant knowledge based on query.

        Args:
            query: Search query for knowledge retrieval.
            **kwargs: Additional parameters:
                - top_k: Maximum number of results (default: 5)
                - min_similarity: Minimum similarity threshold (optional)
                - auto_embed: Whether to auto-embed query if needed (default: True)

        Returns:
            List of relevant messages/documents from knowledge base.
        """
        import asyncio

        top_k = kwargs.get("top_k", 5)
        min_similarity = kwargs.get("min_similarity")
        auto_embed = kwargs.get("auto_embed", True)

        # Generate query embedding
        if auto_embed:
            query_vector = self._run_async(self._embedding_adapter.embed(query)).vector
        else:
            # If auto_embed is False, assume query is already an embedding vector
            if isinstance(query, str):
                raise ValueError("auto_embed=False requires query to be a vector, not a string")
            query_vector = query  # type: ignore

        # Search vector store
        search_results = self._vector_store.search(
            query_embedding=query_vector,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        # Convert documents to messages
        messages: list[Message] = []
        for doc, similarity in search_results:
            message = doc.to_message()
            # Add similarity score to metadata
            message.metadata["similarity"] = similarity
            messages.append(message)

        return messages

    def _run_async(self, coro):
        """Run an async coroutine synchronously.

        Handles both cases: when event loop is running and when it's not.
        """
        import asyncio
        import concurrent.futures

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Event loop is already running, use thread pool
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                # Event loop exists but not running
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)

    def add_document(self, document: Document, auto_embed: bool = True) -> None:
        """Add a document to the knowledge base.

        Args:
            document: Document to add.
            auto_embed: Whether to automatically generate embedding if missing.

        Raises:
            ValueError: If document has no content or embedding generation fails.
        """
        if document.embedding is None and auto_embed:
            # Generate embedding for the document
            embedding_result = self._run_async(
                self._embedding_adapter.embed(document.content)
            )
            document.embedding = embedding_result.vector

        self._vector_store.add(document)

    def add_documents(self, documents: list[Document], auto_embed: bool = True) -> None:
        """Add multiple documents to the knowledge base.

        Args:
            documents: List of documents to add.
            auto_embed: Whether to automatically generate embeddings if missing.
        """
        if auto_embed:
            # Batch embed documents that need embeddings
            docs_to_embed = [doc for doc in documents if doc.embedding is None]
            if docs_to_embed:
                texts = [doc.content for doc in docs_to_embed]
                embedding_results = self._run_async(
                    self._embedding_adapter.embed_batch(texts)
                )

                # Assign embeddings to documents
                for doc, emb_result in zip(docs_to_embed, embedding_results):
                    doc.embedding = emb_result.vector

        self._vector_store.add_batch(documents)

    def remove_document(self, document_id: str) -> bool:
        """Remove a document from the knowledge base.

        Args:
            document_id: Document identifier.

        Returns:
            True if document was removed, False if not found.
        """
        return self._vector_store.remove(document_id)

    def clear(self) -> None:
        """Clear all documents from the knowledge base."""
        self._vector_store.clear()

    @property
    def document_count(self) -> int:
        """Get the number of documents in the knowledge base.

        Returns:
            Number of documents.
        """
        return self._vector_store.count()


__all__ = ["VectorKnowledge"]
