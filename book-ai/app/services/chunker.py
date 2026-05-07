"""
Text chunker: splits extracted paragraphs into overlapping chunks.
Preserves page and paragraph metadata through the chunking process.
"""
from __future__ import annotations

from dataclasses import dataclass
from app.services.pdf_extractor import ExtractedParagraph
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    page_number: int
    paragraph_number: int
    chunk_index: int
    text: str
    original_chapter: str | None
    char_count: int


def _split_into_sentences(text: str) -> list[str]:
    """Naive sentence splitter by common terminators."""
    import re
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_paragraph(
    paragraph: ExtractedParagraph,
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap,
) -> list[TextChunk]:
    """
    Chunk a single paragraph into overlapping text windows.
    If the paragraph is shorter than chunk_size, it is returned as-is.
    """
    text = paragraph.text
    if len(text) <= chunk_size:
        return [
            TextChunk(
                page_number=paragraph.page_number,
                paragraph_number=paragraph.paragraph_number,
                chunk_index=0,
                text=text,
                original_chapter=paragraph.original_chapter,
                char_count=len(text),
            )
        ]

    sentences = _split_into_sentences(text)
    chunks: list[TextChunk] = []
    current: list[str] = []
    current_len = 0
    chunk_idx = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        if current_len + sentence_len > chunk_size and current:
            chunk_text = " ".join(current)
            chunks.append(
                TextChunk(
                    page_number=paragraph.page_number,
                    paragraph_number=paragraph.paragraph_number,
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    original_chapter=paragraph.original_chapter,
                    char_count=len(chunk_text),
                )
            )
            chunk_idx += 1

            # Keep overlap: retain last sentences up to chunk_overlap chars
            overlap_sentences: list[str] = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) <= chunk_overlap:
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s)
                else:
                    break
            current = overlap_sentences
            current_len = overlap_len

        current.append(sentence)
        current_len += sentence_len

    if current:
        chunk_text = " ".join(current)
        chunks.append(
            TextChunk(
                page_number=paragraph.page_number,
                paragraph_number=paragraph.paragraph_number,
                chunk_index=chunk_idx,
                text=chunk_text,
                original_chapter=paragraph.original_chapter,
                char_count=len(chunk_text),
            )
        )

    return chunks


def chunk_paragraphs(
    paragraphs: list[ExtractedParagraph],
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap,
) -> list[TextChunk]:
    """Chunk all extracted paragraphs."""
    all_chunks: list[TextChunk] = []
    for paragraph in paragraphs:
        chunks = chunk_paragraph(paragraph, chunk_size, chunk_overlap)
        all_chunks.extend(chunks)

    logger.info(
        f"Chunked {len(paragraphs)} paragraphs → {len(all_chunks)} chunks "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )
    return all_chunks
