"""
Vector store — pgvector implementation with abstract interface.
The interface allows swapping the backend without changing calling code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.chunk import Chunk

logger = get_logger(__name__)


# ─── Abstract interface ───────────────────────────────────────────────────────

class VectorStore(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    def upsert_chunk(self, db: Session, chunk: Chunk, embedding: list[float]) -> None:
        """Store or update the embedding for a chunk."""
        ...

    @abstractmethod
    def similarity_search(
        self,
        db: Session,
        query_vector: list[float],
        document_id: str,
        top_k: int = 20,
        min_score: float = 0.0,
    ) -> list[tuple[Chunk, float]]:
        """Return the top-k most similar chunks with their cosine similarity scores."""
        ...


# ─── pgvector Implementation ─────────────────────────────────────────────────

class PgVectorStore(VectorStore):
    """
    Vector store backed by PostgreSQL + pgvector.
    Uses cosine distance (<=> operator) for similarity search.
    """

    def upsert_chunk(self, db: Session, chunk: Chunk, embedding: list[float]) -> None:
        chunk.embedding = embedding
        db.add(chunk)
        db.flush()

    def similarity_search(
        self,
        db: Session,
        query_vector: list[float],
        document_id: str,
        top_k: int = 20,
        min_score: float = 0.0,
    ) -> list[tuple[Chunk, float]]:
        """
        Cosine similarity search using pgvector's <=> operator.
        Returns list of (Chunk, score) sorted by similarity descending.
        """
        distance = Chunk.embedding.cosine_distance(query_vector)

        results = (
            db.query(
                Chunk,
                (1 - distance).label("score"),
            )
            .filter(
                Chunk.document_id == document_id,
                Chunk.embedding.isnot(None),
            )
            .order_by(distance)
            .limit(top_k * 3)  # fetch more, filter by min_score after
            .all()
        )

        filtered = [
            (chunk, float(score))
            for chunk, score in results
            if float(score) >= min_score
        ][:top_k]

        logger.debug(
            f"Vector search: {len(filtered)} results above score {min_score} "
            f"(document={document_id})"
        )
        return filtered


# ─── Factory ─────────────────────────────────────────────────────────────────

def get_vector_store() -> VectorStore:
    """Return the configured vector store implementation."""
    return PgVectorStore()
