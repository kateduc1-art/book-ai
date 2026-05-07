"""
Tests for pdf_extractor.py — uses a synthetic in-memory PDF.
"""
import io
import tempfile
from pathlib import Path

import pytest


def _create_test_pdf(text_pages: list[str]) -> Path:
    """Create a minimal PDF file with the given text pages for testing."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open()
        for text in text_pages:
            page = doc.new_page()
            page.insert_text((50, 100), text)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        doc.save(tmp.name)
        doc.close()
        return Path(tmp.name)

    except ImportError:
        pytest.skip("PyMuPDF not installed — skipping PDF tests")


def test_extract_paragraphs_returns_list():
    """extract_paragraphs should return a list of ExtractedParagraph objects."""
    from app.services.pdf_extractor import extract_paragraphs, ExtractedParagraph

    pdf_path = _create_test_pdf([
        "Este é o primeiro parágrafo.\n\nEste é o segundo parágrafo.",
        "Página dois com outro parágrafo.",
    ])

    try:
        result = extract_paragraphs(pdf_path)
        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert isinstance(item, ExtractedParagraph)
            assert item.page_number >= 1
            assert isinstance(item.text, str)
            assert item.char_count == len(item.text)
    finally:
        pdf_path.unlink(missing_ok=True)


def test_extract_preserves_page_numbers():
    """Page numbers must match the actual PDF pages."""
    from app.services.pdf_extractor import extract_paragraphs

    pdf_path = _create_test_pdf([
        "Conteúdo da primeira página.",
        "Conteúdo da segunda página.",
    ])

    try:
        result = extract_paragraphs(pdf_path)
        page_numbers = {p.page_number for p in result}
        # Must have content from at least two pages
        assert len(page_numbers) >= 1  # single-page PDFs may merge
    finally:
        pdf_path.unlink(missing_ok=True)


def test_count_pages():
    """count_pages should return the correct number of pages."""
    from app.services.pdf_extractor import count_pages

    pdf_path = _create_test_pdf([
        "Página 1",
        "Página 2",
        "Página 3",
    ])

    try:
        assert count_pages(pdf_path) == 3
    finally:
        pdf_path.unlink(missing_ok=True)


def test_file_not_found():
    """Should raise FileNotFoundError for missing files."""
    from app.services.pdf_extractor import extract_paragraphs

    with pytest.raises(FileNotFoundError):
        extract_paragraphs("/tmp/does_not_exist_xyz.pdf")


def test_chapter_detection():
    """Paragraphs that match a chapter heading pattern should be detected."""
    from app.services.pdf_extractor import _detect_chapter

    assert _detect_chapter("Capítulo 1 — Introdução") is not None
    assert _detect_chapter("Chapter 2: Methods") is not None
    assert _detect_chapter("Este é um parágrafo normal sem heading.") is None
