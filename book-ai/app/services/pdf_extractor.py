"""
PDF Extractor — Primary: PyMuPDF | Fallback: pdfplumber
Preserves page numbers, paragraph numbers, and tries to detect chapter headings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from app.core.logging import get_logger

logger = get_logger(__name__)

CHAPTER_PATTERN = re.compile(
    r"^\s*(cap[íi]tulo\s+\d+|chapter\s+\d+|\d+[\.\)]\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕ])",
    re.IGNORECASE,
)


@dataclass
class ExtractedParagraph:
    page_number: int
    paragraph_number: int
    text: str
    original_chapter: str | None = None
    char_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.char_count = len(self.text)


def _detect_chapter(text: str) -> str | None:
    """Return the chapter heading if the text line matches a chapter pattern."""
    for line in text.splitlines():
        line = line.strip()
        if CHAPTER_PATTERN.match(line) and len(line) < 200:
            return line
    return None


def _extract_paragraphs_from_text(
    page_text: str, page_number: int, current_chapter: str | None
) -> tuple[list[ExtractedParagraph], str | None]:
    """Split a page's raw text into paragraphs."""
    paragraphs: list[ExtractedParagraph] = []
    blocks = [b.strip() for b in re.split(r"\n{2,}", page_text) if b.strip()]

    for idx, block in enumerate(blocks):
        # Try to detect chapter heading
        detected = _detect_chapter(block)
        if detected:
            current_chapter = detected

        if len(block) < 10:
            continue

        paragraphs.append(
            ExtractedParagraph(
                page_number=page_number,
                paragraph_number=idx,
                text=block,
                original_chapter=current_chapter,
            )
        )

    return paragraphs, current_chapter


# ─── Primary extractor: PyMuPDF ──────────────────────────────────────────────

def _extract_with_pymupdf(pdf_path: Path) -> list[ExtractedParagraph]:
    try:
        import fitz  # PyMuPDF

        paragraphs: list[ExtractedParagraph] = []
        current_chapter: str | None = None

        with fitz.open(str(pdf_path)) as doc:
            for page_idx, page in enumerate(doc, start=1):
                text = page.get_text("text")
                if not text.strip():
                    logger.debug(f"Page {page_idx} has no text (possibly image-based)")
                    continue
                page_paragraphs, current_chapter = _extract_paragraphs_from_text(
                    text, page_idx, current_chapter
                )
                paragraphs.extend(page_paragraphs)
                logger.debug(f"Page {page_idx}: {len(page_paragraphs)} paragraphs extracted")

        return paragraphs

    except ImportError:
        logger.warning("PyMuPDF (fitz) not available. Falling back to pdfplumber.")
        raise


# ─── Fallback extractor: pdfplumber ──────────────────────────────────────────

def _extract_with_pdfplumber(pdf_path: Path) -> list[ExtractedParagraph]:
    import pdfplumber

    paragraphs: list[ExtractedParagraph] = []
    current_chapter: str | None = None

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                logger.debug(f"Page {page_idx} has no text")
                continue
            page_paragraphs, current_chapter = _extract_paragraphs_from_text(
                text, page_idx, current_chapter
            )
            paragraphs.extend(page_paragraphs)

    return paragraphs


# ─── Public API ───────────────────────────────────────────────────────────────

def extract_paragraphs(pdf_path: str | Path) -> list[ExtractedParagraph]:
    """
    Extract all paragraphs from a PDF, with page and paragraph metadata.
    Uses PyMuPDF first; falls back to pdfplumber.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    try:
        paragraphs = _extract_with_pymupdf(path)
        logger.info(f"Extracted {len(paragraphs)} paragraphs via PyMuPDF from '{path.name}'")
        return paragraphs
    except (ImportError, Exception) as e:
        logger.warning(f"PyMuPDF extraction failed ({e}), trying pdfplumber")
        paragraphs = _extract_with_pdfplumber(path)
        logger.info(f"Extracted {len(paragraphs)} paragraphs via pdfplumber from '{path.name}'")
        return paragraphs


def count_pages(pdf_path: str | Path) -> int:
    """Return total number of pages in the PDF."""
    path = Path(pdf_path)
    try:
        import fitz
        with fitz.open(str(path)) as doc:
            return doc.page_count
    except ImportError:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return len(pdf.pages)
