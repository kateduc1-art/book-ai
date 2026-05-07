"""
Topic search service: finds chunks related to a list of topics.
Uses vector search (semantic) + optional keyword boost (hybrid).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.schemas.filter_schema import FilteredChunk
from app.services.embedding_service import get_embedding_provider
from app.services.vector_store import get_vector_store

logger = get_logger(__name__)


def _keyword_boost(text: str, topic: str) -> float:
    """Simple keyword match boost: 0.0 if no words found, up to 0.05."""
    words = [w.lower() for w in topic.split() if len(w) > 3]
    if not words:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for w in words if w in text_lower)
    return min(0.05, matches * 0.01)


def search_by_topics(
    db: Session,
    document_id: str,
    topics: list[str],
    min_score: float = settings.min_score,
    max_results: int = settings.max_results,
) -> list[FilteredChunk]:
    """
    Search for chunks related to the given topics.
    Each topic is embedded separately; results are deduplicated by chunk_id.
    """
    provider = get_embedding_provider()
    vector_store = get_vector_store()

    # Embed all topics at once
    topic_vectors = provider.embed_texts(topics)

    seen_chunk_ids: set[str] = set()
    results: list[FilteredChunk] = []

    for topic, query_vector in zip(topics, topic_vectors):
        hits = vector_store.similarity_search(
            db=db,
            query_vector=query_vector,
            document_id=document_id,
            top_k=max_results,
            min_score=min_score,
        )

        for chunk, base_score in hits:
            if chunk.id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk.id)

            # Apply keyword boost
            boost = _keyword_boost(chunk.text, topic)
            final_score = min(1.0, base_score + boost)

            results.append(
                FilteredChunk(
                    chunk_id=chunk.id,
                    page=chunk.page_number,
                    paragraph=chunk.paragraph_number,
                    text=chunk.text,
                    score=round(final_score, 4),
                    matched_topic=topic,
                )
            )

    # Sort by score descending; limit to max_results
    results.sort(key=lambda r: r.score, reverse=True)
    results = results[:max_results]

    logger.info(
        f"Topic search: {len(results)} results for topics={topics} "
        f"(document={document_id})"
    )
    return results


def get_chunks_by_ids(db: Session, chunk_ids: list[str]) -> list[Chunk]:
    """Retrieve specific chunks by their IDs."""
    return db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
