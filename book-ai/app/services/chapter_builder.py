"""
Chapter builder: assembles a structured Markdown chapter from validated chunks.
Does NOT invent content — only uses the provided text chunks.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.chapter import Chapter
from app.models.chunk import Chunk
from app.schemas.chapter_schema import ChapterSource

logger = get_logger(__name__)


def build_chapter_markdown(
    title: str,
    chunks: list[Chunk],
    topics: list[str],
) -> tuple[str, list[ChapterSource]]:
    """
    Assemble a Markdown chapter from the provided chunks.
    Chunks are ordered by page number then paragraph number.
    Returns (markdown_text, sources).
    """
    if not chunks:
        raise ValueError("No chunks provided to build chapter")

    # Sort by page then paragraph
    ordered = sorted(chunks, key=lambda c: (c.page_number, c.paragraph_number))

    sources: list[ChapterSource] = []
    seen_sources: set[tuple[int, int]] = set()

    lines: list[str] = [
        f"# {title}",
        "",
        f"> **Temas:** {', '.join(topics)}",
        "",
        "---",
        "",
        "## Introdução",
        "",
        (
            "Este capítulo foi compilado a partir de trechos selecionados do documento original, "
            f"abordando os seguintes temas: **{', '.join(topics)}**. "
            "Todos os conteúdos preservam a referência de página da fonte original."
        ),
        "",
        "---",
        "",
        "## Conteúdo",
        "",
    ]

    current_chapter_heading: str | None = None

    for chunk in ordered:
        # Add chapter heading section if it changed
        if chunk.original_chapter and chunk.original_chapter != current_chapter_heading:
            current_chapter_heading = chunk.original_chapter
            lines.append(f"### {current_chapter_heading}")
            lines.append("")

        # Add source reference
        source_key = (chunk.page_number, chunk.paragraph_number)
        if source_key not in seen_sources:
            seen_sources.add(source_key)
            sources.append(
                ChapterSource(page=chunk.page_number, paragraph=chunk.paragraph_number)
            )

        lines.append(f"<!-- Fonte: página {chunk.page_number}, parágrafo {chunk.paragraph_number} -->")
        lines.append(chunk.text)
        lines.append("")
        lines.append(f"*[p. {chunk.page_number}]*")
        lines.append("")

    # Conclusion section
    lines += [
        "---",
        "",
        "## Considerações Finais",
        "",
        (
            "Os trechos reunidos neste capítulo representam as passagens mais relevantes "
            f"sobre **{', '.join(topics)}** encontradas no documento original. "
            "A interpretação e aplicação desses conteúdos deve ser feita com base na leitura "
            "integral da fonte referenciada."
        ),
        "",
        "---",
        "",
        "## Fontes",
        "",
    ]
    for src in sorted(sources, key=lambda s: (s.page, s.paragraph)):
        lines.append(f"- Página {src.page}, Parágrafo {src.paragraph}")
    lines.append("")

    return "\n".join(lines), sources


def create_chapter(
    db: Session,
    document_id: str,
    title: str,
    topics: list[str],
    chunk_ids: list[str],
) -> Chapter:
    """Create and persist a new Chapter from validated chunk IDs."""
    chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
    if not chunks:
        raise ValueError(f"No chunks found for IDs: {chunk_ids}")

    markdown, sources = build_chapter_markdown(title, chunks, topics)

    chapter = Chapter(
        document_id=document_id,
        title=title,
        topics=topics,
        markdown_content=markdown,
        sources=[s.model_dump() for s in sources],
        chunk_ids=chunk_ids,
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)

    logger.info(f"Chapter created: id={chapter.id}, chunks={len(chunks)}")
    return chapter
