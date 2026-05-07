"""
Document indexer: orchestrates the full pipeline of extract → chunk → embed → store.
Called by the API /index endpoint and async job runner.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.services.chunker import chunk_paragraphs
from app.services.embedding_service import get_embedding_provider
from app.services.pdf_extractor import count_pages, extract_paragraphs
from app.services.vector_store import get_vector_store

logger = get_logger(__name__)


ProgressCallback = Callable[[int, str], None]


def index_document(
    db: Session,
    document: Document,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """
    Full indexing pipeline for a document.

    Steps:
        1. Extract paragraphs from PDF
        2. Chunk paragraphs
        3. Generate embeddings
        4. Store chunks + embeddings in DB

    Returns a dict with summary stats.
    """

    def _progress(pct: int, msg: str) -> None:
        if progress_callback:
            progress_callback(pct, msg)
        logger.info(f"[{pct}%] {msg}")

    pdf_path = Path(document.original_path)
    document.status = DocumentStatus.indexing
    db.flush()

    # ── Step 1: Extract ─────────────────────────────────────────────────────
    _progress(5, "Extracting text from PDF")
    paragraphs = extract_paragraphs(pdf_path)
    total_pages = count_pages(pdf_path)
    document.total_pages = total_pages

    # ── Step 2: Chunk ───────────────────────────────────────────────────────
    _progress(20, f"Chunking {len(paragraphs)} paragraphs")
    chunks = chunk_paragraphs(paragraphs)
    _progress(35, f"Created {len(chunks)} chunks")

    # ── Step 3: Embed ───────────────────────────────────────────────────────
    _progress(40, "Generating embeddings")
    provider = get_embedding_provider()
    texts = [c.text for c in chunks]
    vectors = provider.embed_texts(texts)
    _progress(75, f"Generated {len(vectors)} embedding vectors")

    # ── Step 4: Persist ─────────────────────────────────────────────────────
    _progress(80, "Saving chunks to database")
    vector_store = get_vector_store()

    db_chunks: list[Chunk] = []
    for chunk_data, vector in zip(chunks, vectors):
        db_chunk = Chunk(
            document_id=document.id,
            page_number=chunk_data.page_number,
            paragraph_number=chunk_data.paragraph_number,
            chunk_index=chunk_data.chunk_index,
            text=chunk_data.text,
            original_chapter=chunk_data.original_chapter,
            char_count=chunk_data.char_count,
        )
        vector_store.upsert_chunk(db, db_chunk, vector)
        db_chunks.append(db_chunk)

    document.total_chunks = len(db_chunks)
    document.status = DocumentStatus.indexed
    db.commit()

    _progress(100, "Indexing complete")

    return {
        "document_id": document.id,
        "status": DocumentStatus.indexed,
        "pages_processed": total_pages,
        "chunks_created": len(db_chunks),
    }
