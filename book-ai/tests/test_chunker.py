"""
Tests for chunker.py
"""
import pytest
from app.services.pdf_extractor import ExtractedParagraph
from app.services.chunker import chunk_paragraph, chunk_paragraphs, TextChunk


def _make_paragraph(text: str, page: int = 1, para: int = 0) -> ExtractedParagraph:
    return ExtractedParagraph(page_number=page, paragraph_number=para, text=text)


def test_short_paragraph_single_chunk():
    """A paragraph shorter than chunk_size should produce exactly one chunk."""
    para = _make_paragraph("Este é um parágrafo curto.", page=1)
    chunks = chunk_paragraph(para, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert chunks[0].text == para.text


def test_long_paragraph_multiple_chunks():
    """A very long paragraph should be split into multiple chunks."""
    long_text = " ".join([f"Sentença número {i}." for i in range(100)])
    para = _make_paragraph(long_text, page=2)
    chunks = chunk_paragraph(para, chunk_size=200, chunk_overlap=30)
    assert len(chunks) > 1


def test_chunk_preserves_metadata():
    """All chunks from a paragraph must carry the correct page/paragraph metadata."""
    para = _make_paragraph(
        " ".join([f"Palavra {i}." for i in range(200)]),
        page=5,
        para=3,
    )
    chunks = chunk_paragraph(para, chunk_size=100, chunk_overlap=20)
    for chunk in chunks:
        assert chunk.page_number == 5
        assert chunk.paragraph_number == 3
        assert isinstance(chunk, TextChunk)


def test_chunk_index_sequential():
    """chunk_index must be sequential starting from 0."""
    para = _make_paragraph(
        " ".join([f"Frase {i} sobre alfabetização." for i in range(50)]),
        page=1,
    )
    chunks = chunk_paragraph(para, chunk_size=80, chunk_overlap=10)
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_chunk_paragraphs_aggregates():
    """chunk_paragraphs should return chunks from all paragraphs combined."""
    paragraphs = [
        _make_paragraph("Parágrafo curto.", page=1, para=0),
        _make_paragraph("Outro parágrafo curto.", page=1, para=1),
        _make_paragraph("Terceiro parágrafo curto.", page=2, para=0),
    ]
    chunks = chunk_paragraphs(paragraphs, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 3  # each fits in one chunk


def test_empty_paragraphs():
    """chunk_paragraphs with empty list should return empty list."""
    assert chunk_paragraphs([]) == []


def test_char_count_correct():
    """char_count field must match actual text length."""
    para = _make_paragraph("Alfabetização é fundamental.", page=1)
    chunks = chunk_paragraph(para, chunk_size=500)
    for chunk in chunks:
        assert chunk.char_count == len(chunk.text)
