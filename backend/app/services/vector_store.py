"""
Vector Store Service — ChromaDB integration for review embeddings.

Handles:
  - Collection management
  - Embedding generation (OpenAI / placeholder)
  - Adding reviews to the vector store
  - Similarity search for RAG (used in later phases)
"""

import logging
from typing import List, Optional

import chromadb

from app.config import settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Manages the ChromaDB vector store for review embeddings.

    The embedding function is pluggable:
      - If OPENAI_API_KEY is set, uses OpenAI's embedding API.
      - Otherwise, uses ChromaDB's default sentence-transformer.
    """

    def __init__(self):
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection = None
        self._embedding_fn = None

    @property
    def client(self) -> chromadb.ClientAPI:
        """Lazy-init ChromaDB persistent client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
            )
            logger.info("ChromaDB client initialised at %s", settings.CHROMA_PERSIST_DIR)
        return self._client

    @property
    def collection(self):
        """Get or create the reviews collection."""
        if self._collection is None:
            if settings.OPENAI_API_KEY:
                try:
                    from chromadb.utils.embedding_functions import (
                        OpenAIEmbeddingFunction,
                    )
                    self._embedding_fn = OpenAIEmbeddingFunction(
                        api_key=settings.OPENAI_API_KEY,
                        model_name=settings.EMBEDDING_MODEL,
                    )
                    logger.info("Using OpenAI embeddings: %s", settings.EMBEDDING_MODEL)
                except Exception as exc:
                    logger.warning("OpenAI embedding init failed (%s); using default", exc)
                    self._embedding_fn = None

            kwargs = {"name": settings.CHROMA_COLLECTION}
            if self._embedding_fn:
                kwargs["embedding_function"] = self._embedding_fn

            self._collection = self.client.get_or_create_collection(**kwargs)
            logger.info(
                "ChromaDB collection '%s' ready (%d existing docs)",
                settings.CHROMA_COLLECTION,
                self._collection.count(),
            )
        return self._collection

    # ── Public API ───────────────────────────────────────────────────

    def add_reviews(
        self,
        review_ids: List[str],
        texts: List[str],
        metadatas: List[dict],
    ) -> int:
        """
        Add review texts + metadata to the vector store.

        Upserts by ID so re-runs are idempotent.

        Args:
            review_ids: Unique identifiers for each review
            texts:      Review texts to embed
            metadatas:  Per-review metadata dicts

        Returns:
            Number of documents added
        """
        if not review_ids:
            return 0

        batch_size = settings.BATCH_SIZE
        total_added = 0

        for i in range(0, len(review_ids), batch_size):
            batch_ids = review_ids[i : i + batch_size]
            batch_texts = texts[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]

            try:
                self.collection.upsert(
                    ids=batch_ids,
                    documents=batch_texts,
                    metadatas=batch_meta,
                )
                total_added += len(batch_ids)
                logger.debug(
                    "Upserted batch %d–%d (%d docs)",
                    i,
                    i + len(batch_ids),
                    len(batch_ids),
                )
            except Exception as exc:
                logger.error("Vector upsert failed for batch starting at %d: %s", i, exc)

        logger.info("Total embeddings upserted: %d", total_added)
        return total_added

    def search(self, query: str, top_k: int = 10) -> list:
        """
        Semantic similarity search against the review collection.

        Args:
            query:  Natural-language query string
            top_k:  Number of results to return

        Returns:
            ChromaDB query results dict
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )
        return results

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self.collection.count()

    def reset(self) -> None:
        """Delete and recreate the collection (dev/test only)."""
        self.client.delete_collection(settings.CHROMA_COLLECTION)
        self._collection = None
        logger.warning("Collection '%s' reset", settings.CHROMA_COLLECTION)
