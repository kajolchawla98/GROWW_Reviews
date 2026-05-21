"""
Vector Store Service — ChromaDB integration for review embeddings.

Handles:
  - Collection management
  - Embedding generation (placeholder — no OpenAI key needed)
  - Adding reviews to the vector store
  - Similarity search for RAG (used in later phases)

Note: ChromaDB is optional. If it fails to import or initialise (e.g. missing
native libs on some cloud platforms), the service degrades gracefully and the
core pipeline (themes, sentiment, pulse) continues to work normally.
"""

import logging
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Optional import — don't crash the whole app if chromadb isn't available
try:
    import chromadb
    _CHROMA_AVAILABLE = True
except Exception as exc:
    logger.warning("ChromaDB not available (%s) — vector store disabled", exc)
    _CHROMA_AVAILABLE = False


class VectorStoreService:
    """
    Manages the ChromaDB vector store for review embeddings.
    Degrades gracefully if ChromaDB is unavailable.
    """

    def __init__(self):
        self._client = None
        self._collection = None

    @property
    def client(self):
        """Lazy-init ChromaDB persistent client."""
        if not _CHROMA_AVAILABLE:
            return None
        if self._client is None:
            try:
                self._client = chromadb.PersistentClient(
                    path=settings.CHROMA_PERSIST_DIR,
                )
                logger.info("ChromaDB client initialised at %s", settings.CHROMA_PERSIST_DIR)
            except Exception as exc:
                logger.warning("ChromaDB client init failed: %s — vector store disabled", exc)
                return None
        return self._client

    @property
    def collection(self):
        """Get or create the reviews collection."""
        if self.client is None:
            return None
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(
                    name=settings.CHROMA_COLLECTION
                )
                logger.info(
                    "ChromaDB collection '%s' ready (%d existing docs)",
                    settings.CHROMA_COLLECTION,
                    self._collection.count(),
                )
            except Exception as exc:
                logger.warning("ChromaDB collection init failed: %s", exc)
                return None
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
        Returns 0 silently if ChromaDB is unavailable.
        """
        if not review_ids or self.collection is None:
            return 0

        batch_size = settings.BATCH_SIZE
        total_added = 0

        for i in range(0, len(review_ids), batch_size):
            batch_ids = review_ids[i: i + batch_size]
            batch_texts = texts[i: i + batch_size]
            batch_meta = metadatas[i: i + batch_size]
            try:
                self.collection.upsert(
                    ids=batch_ids,
                    documents=batch_texts,
                    metadatas=batch_meta,
                )
                total_added += len(batch_ids)
            except Exception as exc:
                logger.error("Vector upsert failed for batch at %d: %s", i, exc)

        logger.info("Total embeddings upserted: %d", total_added)
        return total_added

    def search(self, query: str, top_k: int = 10) -> list:
        """Semantic similarity search. Returns empty list if unavailable."""
        if self.collection is None:
            return []
        try:
            return self.collection.query(query_texts=[query], n_results=top_k)
        except Exception as exc:
            logger.error("Vector search failed: %s", exc)
            return []

    def count(self) -> int:
        """Return number of documents in the collection, or 0 if unavailable."""
        if self.collection is None:
            return 0
        try:
            return self.collection.count()
        except Exception:
            return 0

    def reset(self) -> None:
        """Delete and recreate the collection (dev/test only)."""
        if self.client is None:
            return
        try:
            self.client.delete_collection(settings.CHROMA_COLLECTION)
            self._collection = None
            logger.warning("Collection '%s' reset", settings.CHROMA_COLLECTION)
        except Exception as exc:
            logger.error("Collection reset failed: %s", exc)
