"""
Tests for chapter_builder.py — uses mock Chunk objects (no DB required).
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services.chapter_builder import build_chapter_markdown
from app.schemas.chapter_schema import ChapterSource


def _make_mock_chunk(page: int, paragraph: int, text: str, chapter: str | None = None):
    chunk = MagicMock()
    chunk.id = str(uuid.uuid4())
    chunk.page_number = page
    chunk.paragraph_number = paragraph
    chunk.text = text
    chunk.original_chapter = chapter
    return chunk


def test_build_chapter_markdown_basic():
    """Should return Markdown string and list of sources."""
    chunks = [
        _make_mock_chunk(1, 0, "Texto sobre consciência fonológica."),
        _make_mock_chunk(2, 1, "Mais informações sobre alfabetização."),
    ]
    markdown, sources = build_chapter_markdown(
        title="Teste de Capítulo",
        chunks=chunks,
        topics=["consciência fonológica"],
    )

    assert isinstance(markdown, str)
    assert "# Teste de Capítulo" in markdown
    assert "consciência fonológica" in markdown.lower() or "Consciência" in markdown
    assert len(sources) == 2
    for src in sources:
        assert isinstance(src, ChapterSource)


def test_build_chapter_preserves_page_refs():
    """The page reference *[p. X]* must appear in the output for each chunk."""
    chunks = [_make_mock_chunk(7, 0, "Conteúdo da página sete.")]
    markdown, _ = build_chapter_markdown("Título", chunks, ["tema"])
    assert "*[p. 7]*" in markdown


def test_build_chapter_orders_by_page():
    """Chunks must be ordered by page then paragraph in the output."""
    chunks = [
        _make_mock_chunk(3, 0, "Página 3, parágrafo 0."),
        _make_mock_chunk(1, 0, "Página 1, parágrafo 0."),
        _make_mock_chunk(2, 0, "Página 2, parágrafo 0."),
    ]
    markdown, sources = build_chapter_markdown("Ordem", chunks, ["tema"])

    # Sources should be sorted by page
    pages = [s.page for s in sources]
    assert pages == sorted(pages)


def test_build_chapter_empty_raises():
    """Empty chunks should raise ValueError."""
    with pytest.raises(ValueError):
        build_chapter_markdown("Título", [], ["tema"])


def test_build_chapter_includes_conclusion():
    """The Markdown should include a conclusion/final section."""
    chunks = [_make_mock_chunk(1, 0, "Algum conteúdo.")]
    markdown, _ = build_chapter_markdown("Título", chunks, ["tema"])
    assert "Considerações Finais" in markdown or "Fontes" in markdown


def test_build_chapter_sources_unique():
    """Duplicate (page, paragraph) pairs should appear only once in sources."""
    chunks = [
        _make_mock_chunk(5, 2, "Primeiro trecho da mesma posição."),
        _make_mock_chunk(5, 2, "Segundo trecho da mesma posição."),
    ]
    _, sources = build_chapter_markdown("Título", chunks, ["tema"])
    # The deduplicated source list should have at most 1 entry for (5, 2)
    source_keys = [(s.page, s.paragraph) for s in sources]
    assert len(source_keys) == len(set(source_keys))
